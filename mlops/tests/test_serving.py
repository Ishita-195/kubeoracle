"""
Unit tests for mlops/serving/predictor.py (the MLOps-aware predictor).
"""
import pickle
from pathlib import Path

import numpy as np
import pytest


def _make_pipeline():
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", xgb.XGBClassifier(n_estimators=10, max_depth=2,
                                  use_label_encoder=False, eval_metric="logloss",
                                  verbosity=0)),
    ])
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 100, size=(60, 5))
    y = (X[:, 0] > 50).astype(int)
    pipe.fit(X, y)
    return pipe


@pytest.fixture
def fresh(monkeypatch):
    """Reset the predictor's module-level cache before each test."""
    import predictor as p
    monkeypatch.setattr(p, "_model", None)
    monkeypatch.setattr(p, "_model_loaded_at", 0.0)
    return p


def test_fallback_when_no_registry(fresh, monkeypatch):
    monkeypatch.setattr(fresh, "_MODEL_PROD", Path("/nonexistent/a.pkl"))
    monkeypatch.setattr(fresh, "_MODEL_LATEST", Path("/nonexistent/b.pkl"))
    prob = fresh.predict_failure_probability(95, 95, 9, 9500, 80)
    assert 0 <= prob <= 100


def test_train_fallback_direct(fresh):
    pipe = fresh._train_fallback()
    proba = pipe.predict_proba(np.array([[50, 50, 1, 500, 10]]))
    assert proba.shape == (1, 2)


def test_load_from_registry(fresh, monkeypatch, tmp_path):
    prod = tmp_path / "model_production.pkl"
    with open(prod, "wb") as f:
        pickle.dump(_make_pipeline(), f)
    monkeypatch.setattr(fresh, "_MODEL_PROD", prod)
    monkeypatch.setattr(fresh, "_MODEL_LATEST", tmp_path / "model_latest.pkl")

    assert fresh.get_model() is not None
    assert fresh.reload_model()["source"] == "registry"


def test_reload_reports_fallback_source(fresh, monkeypatch):
    monkeypatch.setattr(fresh, "_MODEL_PROD", Path("/nonexistent/a.pkl"))
    monkeypatch.setattr(fresh, "_MODEL_LATEST", Path("/nonexistent/b.pkl"))
    assert fresh.reload_model()["source"] == "in-memory fallback"


def test_load_from_registry_handles_corrupt_file(fresh, monkeypatch, tmp_path):
    bad = tmp_path / "model_production.pkl"
    bad.write_bytes(b"this is not a pickle")
    monkeypatch.setattr(fresh, "_MODEL_PROD", bad)
    monkeypatch.setattr(fresh, "_MODEL_LATEST", tmp_path / "missing.pkl")
    assert fresh._load_from_registry() is None


def test_model_is_cached_within_ttl(fresh, monkeypatch, tmp_path):
    prod = tmp_path / "model_production.pkl"
    with open(prod, "wb") as f:
        pickle.dump(_make_pipeline(), f)
    monkeypatch.setattr(fresh, "_MODEL_PROD", prod)
    monkeypatch.setattr(fresh, "_MODEL_LATEST", tmp_path / "model_latest.pkl")
    monkeypatch.setattr(fresh, "_MODEL_TTL_SEC", 9999.0)
    assert fresh.get_model() is fresh.get_model()
