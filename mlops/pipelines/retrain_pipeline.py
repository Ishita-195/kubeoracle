"""
mlops/pipelines/retrain_pipeline.py
KubeOracle Automated Retraining Pipeline

Triggered by:
  - Scheduled cron (e.g. nightly, weekly)
  - Drift alert from monitor.py (PSI threshold crossed)
  - Manual invocation

Flow:
  1. Check drift report — skip retraining if no drift
  2. Generate / refresh training data
  3. Run training pipeline (all hyperparameter trials)
  4. Compare new model vs. current production (champion/challenger)
  5. Promote new model only if it beats production by MIN_IMPROVEMENT
  6. Log outcome to pipeline_runs.jsonl

Usage:
    python retrain_pipeline.py               # auto-check drift, retrain if needed
    python retrain_pipeline.py --force       # always retrain regardless of drift
    python retrain_pipeline.py --dry-run     # check drift, report, but don't retrain
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kubeoracle.pipeline")

ROOT         = Path(__file__).resolve().parents[2]
PIPELINE_LOG = Path(__file__).parent / "pipeline_runs.jsonl"

# Minimum AUC improvement required to promote challenger over champion
MIN_IMPROVEMENT = float("0.005")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log_run(outcome: dict) -> None:
    outcome["ts"] = datetime.utcnow().isoformat()
    with open(PIPELINE_LOG, "a") as f:
        f.write(json.dumps(outcome) + "\n")
    logger.info("📝 Pipeline run logged → %s", PIPELINE_LOG)


def _current_production_auc() -> float | None:
    """Return the AUC of the current production model from the registry."""
    registry_file = ROOT / "mlops" / "model_registry" / "registry.json"
    if not registry_file.exists():
        return None
    with open(registry_file) as f:
        reg = json.load(f)
    prod_ver = reg.get("production")
    if not prod_ver:
        return None
    return reg["versions"].get(prod_ver, {}).get("metrics", {}).get("roc_auc")


def _check_drift_needed() -> tuple[bool, list[str]]:
    """Return (should_retrain, reasons)."""
    sys.path.insert(0, str(ROOT / "mlops" / "monitoring"))
    from monitor import compute_drift_report

    report  = compute_drift_report()
    reasons = []

    critical = [a for a in report["alerts"] if a.get("level") == "critical"]
    warnings = [a for a in report["alerts"] if a.get("level") == "warning"]

    for a in critical:
        reasons.append(f"[CRITICAL] {a['message']}")
    for a in warnings:
        reasons.append(f"[WARNING]  {a['message']}")

    should_retrain = len(critical) > 0
    return should_retrain, reasons


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(force: bool = False, dry_run: bool = False, n_samples: int = 3000) -> dict:
    logger.info("═" * 55)
    logger.info("🚀 KubeOracle Retraining Pipeline — %s", datetime.utcnow().isoformat())
    logger.info("═" * 55)

    outcome = {
        "force":    force,
        "dry_run":  dry_run,
        "retrained": False,
        "promoted":  False,
        "skipped_reason": None,
    }

    # ── Step 1: Drift check ───────────────────────────────────────────────────
    if not force:
        should_retrain, reasons = _check_drift_needed()
        if not should_retrain:
            msg = "No critical drift detected — skipping retraining."
            logger.info("✅ %s", msg)
            if reasons:
                for r in reasons:
                    logger.info("   %s", r)
            outcome["skipped_reason"] = msg
            _log_run(outcome)
            return outcome
        logger.warning("⚠️  Drift detected — retraining triggered:")
        for r in reasons:
            logger.warning("   %s", r)
        outcome["drift_reasons"] = reasons
    else:
        logger.info("🔧 --force flag set — skipping drift check.")

    if dry_run:
        logger.info("🧪 --dry-run: would retrain here. Exiting early.")
        outcome["skipped_reason"] = "dry-run"
        _log_run(outcome)
        return outcome

    # ── Step 2: Train ─────────────────────────────────────────────────────────
    sys.path.insert(0, str(ROOT / "mlops" / "training"))
    from train import run_training

    logger.info("🔬 Starting training run …")
    best_run = run_training(
        experiment_name="kubeoracle-failure-prediction-auto",
        n_samples=n_samples,
    )
    outcome["retrained"]     = True
    outcome["new_version"]   = best_run.get("metrics", {})
    new_auc = best_run["metrics"].get("roc_auc", 0)
    logger.info("New model AUC: %.4f", new_auc)

    # ── Step 3: Champion / Challenger ─────────────────────────────────────────
    prod_auc = _current_production_auc()
    if prod_auc is None:
        logger.info("No production model yet — promoting new model automatically.")
        should_promote = True
    else:
        improvement = new_auc - prod_auc
        logger.info("Champion AUC: %.4f | Challenger AUC: %.4f | Δ=%.4f",
                    prod_auc, new_auc, improvement)
        should_promote = improvement >= MIN_IMPROVEMENT

    # ── Step 4: Promote ───────────────────────────────────────────────────────
    if should_promote:
        sys.path.insert(0, str(ROOT / "mlops" / "model_registry"))
        from registry import list_versions, promote

        versions = list_versions()
        if versions:
            latest_ver = versions[0]["version"]   # sorted newest-first
            promote(latest_ver)
            outcome["promoted"]         = True
            outcome["promoted_version"] = latest_ver
            logger.info("✅ Promoted version '%s' to production.", latest_ver)
        else:
            logger.warning("No versions found in registry after training?!")
    else:
        logger.info("🏆 Champion model retained (improvement %.4f < threshold %.4f).",
                    new_auc - (prod_auc or 0), MIN_IMPROVEMENT)
        outcome["skipped_reason"] = "challenger did not beat champion"

    _log_run(outcome)
    logger.info("═" * 55)
    logger.info("Pipeline complete.")
    return outcome


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KubeOracle retraining pipeline")
    parser.add_argument("--force",     action="store_true", help="Retrain regardless of drift")
    parser.add_argument("--dry-run",   action="store_true", help="Check drift but don't retrain")
    parser.add_argument("--n-samples", type=int, default=3000, help="Training dataset size")
    args = parser.parse_args()

    result = run_pipeline(force=args.force, dry_run=args.dry_run, n_samples=args.n_samples)
    promoted = result.get("promoted")
    retrained = result.get("retrained")
    print("\n📊 Pipeline summary:")
    print(f"  Retrained : {retrained}")
    print(f"  Promoted  : {promoted}")
    if result.get("skipped_reason"):
        print(f"  Skipped   : {result['skipped_reason']}")
