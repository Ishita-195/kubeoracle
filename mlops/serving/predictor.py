"""
mlops/serving/predictor.py
KubeOracle MLOps-Aware Predictor

Drop-in replacement for backend/ml/predictor.py.
Loads the production model from the Model Registry instead of
training in-memory on every startup.

Falls back to in-memory training if no registry model exists
(safe during initial bootstrap or CI).
"""

import logging
import os
import time
from pathlib import Path
from threading import Lock

import numpy as np
from sklearn.pipeline import Pipeline

logger = logging.getLogger("kubeoracle.predictor")

# ─── Model Registry path (resolve relative to this file) ────────────────────
_REGISTRY_DIR   = Path(__file__).resolve().parents[2] / "mlops" / "model_registry" / "artifacts"
_MODEL_PROD     = _REGISTRY_DIR / "model_production.pkl"
_MODEL_LATEST   = _REGISTRY_DIR / "model_latest.pkl"

# ─── Thread-safe model cache ──────────────────────────────────────────────────
_model_lock    : Lock            = Lock()
_model         : Pipeline | None = None
_model_loaded_at: float          = 0.0
_MODEL_TTL_SEC : float           = float(os.getenv("MODEL_TTL_SEC", "300"))   # reload every 5 min


def _load_from_registry() -> Pipeline | None:
    """Try to load the production (or latest) model from the registry."""
    import pickle

    for candidate in [_MODEL_PROD, _MODEL_LATEST]:
        if candidate.exists():
            try:
                with open(candidate, "rb") as f:
                    pipe = pickle.load(f)
                logger.info("✅ Loaded model from registry: %s", candidate.name)
                return pipe
            except Exception as exc:
                logger.warning("Registry load failed (%s): %s", candidate.name, exc)

    return None


def _train_fallback() -> Pipeline:
    """Train a fresh model in-memory (original behavior — always safe)."""
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler

    logger.warning("⚠️  No registry model found — training in-memory fallback.")
    rng = np.random.default_rng(42)
    n   = 2000
    X, y = [], []
    for _ in range(n):
        cpu, mem, rst = rng.uniform(5, 100), rng.uniform(10, 100), int(rng.integers(0, 10))
        lat, err      = rng.uniform(20, 10000), rng.uniform(0, 100)
        fail = (cpu > 85 and mem > 80) or rst >= 3 or err > 20 or (lat > 3000 and err > 5)
        X.append([cpu, mem, rst, lat, err])
        y.append(int(fail))

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", xgb.XGBClassifier(
            n_estimators=80, max_depth=4, learning_rate=0.15,
            use_label_encoder=False, eval_metric="logloss", verbosity=0,
        )),
    ])
    pipe.fit(np.array(X), np.array(y))
    logger.info("✅ In-memory fallback model trained.")
    return pipe


def get_model() -> Pipeline:
    """Return the current model, reloading from registry if TTL has expired."""
    global _model, _model_loaded_at

    now = time.monotonic()
    with _model_lock:
        if _model is None or (now - _model_loaded_at) > _MODEL_TTL_SEC:
            candidate = _load_from_registry()
            _model = candidate if candidate is not None else _train_fallback()
            _model_loaded_at = now

    return _model


def predict_failure_probability(
    cpu: float, memory: float, restarts: int, latency: float, error_rate: float
) -> float:
    """
    Returns failure probability as 0–100.
    API-compatible with the original backend/ml/predictor.py.
    """
    model    = get_model()
    features = np.array([[cpu, memory, restarts, latency, error_rate]])
    prob     = model.predict_proba(features)[0][1]
    return round(float(prob) * 100, 1)


def reload_model() -> dict:
    """Force-reload the model from the registry. Called by the /admin/reload endpoint."""
    global _model, _model_loaded_at
    with _model_lock:
        candidate    = _load_from_registry()
        _model       = candidate if candidate is not None else _train_fallback()
        _model_loaded_at = time.monotonic()
    source = "registry" if candidate is not None else "in-memory fallback"
    return {"status": "reloaded", "source": source}
