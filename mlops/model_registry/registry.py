"""
mlops/model_registry/registry.py
KubeOracle Model Registry

Tracks all trained model versions, promotes a version to 'production',
and provides a safe rollback mechanism.

Usage (CLI):
    python registry.py list
    python registry.py promote <version>
    python registry.py rollback
    python registry.py info <version>
"""

import json
import pickle
import sys
from datetime import datetime
from pathlib import Path

REGISTRY_DIR   = Path(__file__).parent
ARTIFACTS_DIR  = REGISTRY_DIR / "artifacts"
REGISTRY_FILE  = REGISTRY_DIR / "registry.json"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"versions": {}, "production": None, "previous_production": None}


def _save_registry(reg: dict) -> None:
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def list_versions() -> list[dict]:
    """Return all registered model versions sorted by registration date."""
    reg = _load_registry()
    versions = []
    for ver, meta in reg["versions"].items():
        entry = dict(meta)
        entry["version"] = ver
        entry["is_production"] = (ver == reg["production"])
        versions.append(entry)
    versions.sort(key=lambda x: x.get("registered_at", ""), reverse=True)
    return versions


def promote(version: str) -> None:
    """Promote a model version to production (creates 'model_production.pkl' symlink)."""
    reg = _load_registry()

    if version not in reg["versions"]:
        raise ValueError(f"Version '{version}' not found in registry.")

    model_path = ARTIFACTS_DIR / f"model_{version}.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Artifact missing: {model_path}")

    # Remember previous production for rollback
    reg["previous_production"] = reg["production"]

    # Update symlink
    prod_link = ARTIFACTS_DIR / "model_production.pkl"
    if prod_link.exists() or prod_link.is_symlink():
        prod_link.unlink()
    prod_link.symlink_to(model_path.name)

    reg["production"] = version
    reg["versions"][version]["promoted_at"] = datetime.utcnow().isoformat()
    _save_registry(reg)
    print(f"✅ Version '{version}' promoted to PRODUCTION")
    print(f"   Symlink: {prod_link} → {model_path.name}")


def rollback() -> None:
    """Roll back to the previous production version."""
    reg = _load_registry()
    prev = reg.get("previous_production")
    if not prev:
        print("❌ No previous production version to roll back to.")
        return
    print(f"↩️  Rolling back: {reg['production']} → {prev}")
    promote(prev)


def get_production_model():
    """Load and return the production model pipeline."""
    # Try production symlink first
    prod_link = ARTIFACTS_DIR / "model_production.pkl"
    if prod_link.exists():
        with open(prod_link, "rb") as f:
            return pickle.load(f)

    # Fall back to 'latest' symlink (set by training pipeline)
    latest = ARTIFACTS_DIR / "model_latest.pkl"
    if latest.exists():
        print("⚠️  No production model set — using model_latest.pkl")
        with open(latest, "rb") as f:
            return pickle.load(f)

    raise RuntimeError("No trained model found. Run train.py first.")


def register_from_meta(meta_path: Path) -> None:
    """Register a model version from its metadata JSON (called by train.py)."""
    with open(meta_path) as f:
        meta = json.load(f)

    reg = _load_registry()
    version = meta["version"]
    reg["versions"][version] = {
        "mlflow_run_id": meta.get("mlflow_run_id"),
        "params":        meta.get("params", {}),
        "metrics":       meta.get("metrics", {}),
        "features":      meta.get("features", []),
        "registered_at": meta.get("registered_at"),
    }
    _save_registry(reg)
    print(f"📋 Registered version '{version}' in registry.")


def info(version: str) -> dict:
    reg = _load_registry()
    if version not in reg["versions"]:
        raise ValueError(f"Version '{version}' not in registry.")
    return {"version": version, **reg["versions"][version],
            "is_production": version == reg["production"]}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _cli():
    args = sys.argv[1:]
    if not args:
        print("Usage: registry.py <list|promote|rollback|info> [version]")
        sys.exit(1)

    cmd = args[0]

    if cmd == "list":
        versions = list_versions()
        if not versions:
            print("No registered models yet. Run train.py first.")
            return
        print(f"\n{'VERSION':<22} {'AUC':>6} {'F1':>6} {'PROD':>6}  REGISTERED_AT")
        print("-" * 70)
        for v in versions:
            auc  = v.get("metrics", {}).get("roc_auc", "—")
            f1   = v.get("metrics", {}).get("f1", "—")
            prod = "★" if v["is_production"] else ""
            print(f"{v['version']:<22} {str(auc):>6} {str(f1):>6} {prod:>6}  {v.get('registered_at', '—')}")

    elif cmd == "promote":
        if len(args) < 2:
            print("Usage: registry.py promote <version>")
            sys.exit(1)
        promote(args[1])

    elif cmd == "rollback":
        rollback()

    elif cmd == "info":
        if len(args) < 2:
            print("Usage: registry.py info <version>")
            sys.exit(1)
        data = info(args[1])
        print(json.dumps(data, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
