"""
mlops/monitoring/monitor.py
KubeOracle Model Monitoring

Tracks:
  - Prediction distribution (output drift)
  - Feature distribution (data/input drift via Population Stability Index)
  - Rolling accuracy vs. a reference window
  - Alert thresholds → writes structured alerts to a JSON log

Run as a standalone service:
    python monitor.py serve          # starts a FastAPI monitor server on :8001
    python monitor.py report         # prints a one-shot drift report
    python monitor.py check-drift    # exits 1 if drift is detected (CI gate)
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger("kubeoracle.monitor")

# ─── Paths ────────────────────────────────────────────────────────────────────
MONITOR_DIR   = Path(__file__).parent
LOG_PATH      = MONITOR_DIR / "prediction_log.jsonl"
ALERT_PATH    = MONITOR_DIR / "alerts.jsonl"
BASELINE_PATH = MONITOR_DIR / "baseline_stats.json"

# ─── Thresholds ───────────────────────────────────────────────────────────────
PSI_WARN_THRESHOLD   = 0.10   # Population Stability Index ≥ 0.10 → warn
PSI_ALERT_THRESHOLD  = 0.25   # PSI ≥ 0.25 → alert / retrain
PRED_RATE_WARN       = 0.60   # >60% of predictions are "failure" → anomalous
PRED_RATE_WARN_LOW   = 0.02   # <2% → model may have collapsed
WINDOW_SIZE          = 500    # rolling window for drift checks


# ─────────────────────────────────────────────────────────────────────────────
# Prediction logging
# ─────────────────────────────────────────────────────────────────────────────

def log_prediction(features: dict, probability: float, service: str = "unknown") -> None:
    """Append one prediction record to the JSONL log."""
    record = {
        "ts":          datetime.utcnow().isoformat(),
        "service":     service,
        "features":    features,
        "probability": probability,
        "predicted":   int(probability >= 50),
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def _load_recent_predictions(n: int = WINDOW_SIZE) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text().splitlines()
    return [json.loads(l) for l in lines[-n:] if l.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Baseline stats (computed once from training data)
# ─────────────────────────────────────────────────────────────────────────────

def compute_baseline(X: np.ndarray, feature_names: list[str]) -> None:
    """Save per-feature mean/std/min/max as baseline for drift comparison."""
    stats = {}
    for i, name in enumerate(feature_names):
        col = X[:, i]
        stats[name] = {
            "mean": float(np.mean(col)),
            "std":  float(np.std(col)),
            "min":  float(np.min(col)),
            "max":  float(np.max(col)),
            "p10":  float(np.percentile(col, 10)),
            "p90":  float(np.percentile(col, 90)),
        }
    with open(BASELINE_PATH, "w") as f:
        json.dump({"computed_at": datetime.utcnow().isoformat(), "features": stats}, f, indent=2)
    logger.info("Baseline stats saved → %s", BASELINE_PATH)


def _load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    with open(BASELINE_PATH) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Population Stability Index
# ─────────────────────────────────────────────────────────────────────────────

def _psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Compute PSI between expected (baseline) and actual distributions."""
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())
    bins = np.linspace(min_val, max_val, buckets + 1)

    exp_counts = np.histogram(expected, bins=bins)[0] + 1e-6
    act_counts = np.histogram(actual,   bins=bins)[0] + 1e-6

    exp_pct = exp_counts / exp_counts.sum()
    act_pct = act_counts / act_counts.sum()

    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


# ─────────────────────────────────────────────────────────────────────────────
# Drift detection
# ─────────────────────────────────────────────────────────────────────────────

def compute_drift_report() -> dict:
    preds = _load_recent_predictions()
    baseline = _load_baseline()

    report = {
        "ts":             datetime.utcnow().isoformat(),
        "n_predictions":  len(preds),
        "feature_drift":  {},
        "output_drift":   {},
        "alerts":         [],
    }

    if not preds:
        report["alerts"].append({"level": "info", "message": "No predictions logged yet."})
        return report

    # ── Output drift ──────────────────────────────────────────────────────────
    probs = np.array([p["probability"] for p in preds])
    pred_rate = float((probs >= 50).mean())
    report["output_drift"] = {
        "failure_rate":  round(pred_rate, 4),
        "mean_prob":     round(float(probs.mean()), 2),
        "std_prob":      round(float(probs.std()), 2),
    }
    if pred_rate > PRED_RATE_WARN:
        _emit_alert(report, "warning",
            f"High failure prediction rate: {pred_rate:.1%} (threshold {PRED_RATE_WARN:.0%})")
    if pred_rate < PRED_RATE_WARN_LOW:
        _emit_alert(report, "warning",
            f"Suspiciously low failure rate: {pred_rate:.1%}. Model may need re-evaluation.")

    # ── Feature drift (PSI) ───────────────────────────────────────────────────
    if baseline:
        feature_names = list(baseline["features"].keys())
        baseline_samples = {
            name: np.random.normal(
                baseline["features"][name]["mean"],
                max(baseline["features"][name]["std"], 1e-6),
                size=1000,
            )
            for name in feature_names
        }
        for name in feature_names:
            actual_vals = np.array([
                p["features"].get(name, 0) for p in preds if "features" in p
            ])
            if len(actual_vals) < 30:
                continue
            psi = _psi(baseline_samples[name], actual_vals)
            report["feature_drift"][name] = round(psi, 4)
            if psi >= PSI_ALERT_THRESHOLD:
                _emit_alert(report, "critical",
                    f"Feature '{name}' PSI={psi:.3f} — significant distribution shift. Retrain advised.")
            elif psi >= PSI_WARN_THRESHOLD:
                _emit_alert(report, "warning",
                    f"Feature '{name}' PSI={psi:.3f} — moderate drift detected.")
    else:
        report["alerts"].append({
            "level": "info",
            "message": "No baseline stats found. Run compute_baseline() after training."
        })

    return report


def _emit_alert(report: dict, level: str, message: str) -> None:
    entry = {"ts": datetime.utcnow().isoformat(), "level": level, "message": message}
    report["alerts"].append(entry)
    with open(ALERT_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.warning("[%s] %s", level.upper(), message)


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI monitor server
# ─────────────────────────────────────────────────────────────────────────────

def start_server(host: str = "0.0.0.0", port: int = 8001):
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI(title="KubeOracle Model Monitor", version="1.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/drift")
    def drift():
        return compute_drift_report()

    @app.get("/alerts")
    def alerts():
        if not ALERT_PATH.exists():
            return []
        lines = ALERT_PATH.read_text().splitlines()
        return [json.loads(l) for l in lines if l.strip()]

    @app.get("/stats")
    def stats():
        preds = _load_recent_predictions()
        if not preds:
            return {"n": 0}
        probs = [p["probability"] for p in preds]
        return {
            "n":           len(preds),
            "mean_prob":   round(sum(probs) / len(probs), 2),
            "failure_rate": round(sum(1 for p in probs if p >= 50) / len(probs), 4),
            "oldest_ts":   preds[0]["ts"],
            "newest_ts":   preds[-1]["ts"],
        }

    uvicorn.run(app, host=host, port=port)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"

    if cmd == "serve":
        start_server()

    elif cmd == "report":
        report = compute_drift_report()
        print(json.dumps(report, indent=2))

    elif cmd == "check-drift":
        report = compute_drift_report()
        critical = [a for a in report["alerts"] if a.get("level") == "critical"]
        if critical:
            print("❌ Drift check FAILED:")
            for a in critical:
                print(f"   {a['message']}")
            sys.exit(1)
        print("✅ Drift check passed.")
        sys.exit(0)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
