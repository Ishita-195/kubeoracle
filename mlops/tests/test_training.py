"""
mlops/tests/test_training.py
Unit tests for the KubeOracle MLOps training pipeline
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure imports resolve regardless of working directory
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mlops" / "training"))
sys.path.insert(0, str(ROOT / "mlops" / "model_registry"))
sys.path.insert(0, str(ROOT / "mlops" / "monitoring"))
sys.path.insert(0, str(ROOT / "mlops" / "serving"))


# ─── Training ────────────────────────────────────────────────────────────────

class TestDataGeneration:
    def test_shape(self):
        from train import generate_synthetic_data
        X, y = generate_synthetic_data(n=200)
        assert X.shape == (200, 5)
        assert y.shape == (200,)

    def test_labels_binary(self):
        from train import generate_synthetic_data
        _, y = generate_synthetic_data(n=200)
        assert set(y).issubset({0, 1})

    def test_positive_rate_reasonable(self):
        from train import generate_synthetic_data
        _, y = generate_synthetic_data(n=1000)
        rate = y.mean()
        assert 0.05 < rate < 0.90, f"Unexpected positive rate: {rate:.2%}"

    def test_snapshot_saved(self, tmp_path, monkeypatch):
        import train
        monkeypatch.setattr(train, "DATA_DIR", tmp_path)
        train.generate_synthetic_data(n=100)
        snapshots = list(tmp_path.glob("dataset_*.json"))
        assert len(snapshots) == 1
        data = json.loads(snapshots[0].read_text())
        assert data["n_samples"] == 100
        assert "features" in data


class TestModelBuilding:
    def test_pipeline_trains(self):
        from train import build_pipeline, generate_synthetic_data
        X, y = generate_synthetic_data(n=300)
        pipe = build_pipeline({"n_estimators": 20, "max_depth": 3, "learning_rate": 0.1})
        pipe.fit(X, y)
        preds = pipe.predict(X[:5])
        assert preds.shape == (5,)

    def test_predict_proba_shape(self):
        from train import build_pipeline, generate_synthetic_data
        X, y = generate_synthetic_data(n=300)
        pipe = build_pipeline({"n_estimators": 20, "max_depth": 3, "learning_rate": 0.1})
        pipe.fit(X, y)
        proba = pipe.predict_proba(X[:5])
        assert proba.shape == (5, 2)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)


class TestEvaluation:
    @pytest.fixture(scope="class")
    def trained_pipe(self):
        from train import build_pipeline, generate_synthetic_data
        X, y = generate_synthetic_data(n=500)
        pipe = build_pipeline({"n_estimators": 30, "max_depth": 3, "learning_rate": 0.1})
        pipe.fit(X, y)
        return pipe, X, y

    def test_metrics_keys(self, trained_pipe):
        from train import evaluate
        pipe, X, y = trained_pipe
        metrics = evaluate(pipe, X, y)
        for k in ["accuracy", "precision", "recall", "f1", "roc_auc", "report"]:
            assert k in metrics

    def test_auc_reasonable(self, trained_pipe):
        from train import evaluate
        pipe, X, y = trained_pipe
        metrics = evaluate(pipe, X, y)
        assert metrics["roc_auc"] > 0.70, f"AUC too low: {metrics['roc_auc']}"


# ─── Predictor (serving layer) ────────────────────────────────────────────────

class TestPredictor:
    def test_fallback_probability_range(self, monkeypatch):
        """Without a registry model the fallback trainer should still produce valid output."""
        from predictor import predict_failure_probability
        # Force fallback by pointing to nonexistent registry
        import predictor as pred_module
        monkeypatch.setattr(pred_module, "_MODEL_PROD",   Path("/nonexistent/model.pkl"))
        monkeypatch.setattr(pred_module, "_MODEL_LATEST", Path("/nonexistent/model.pkl"))
        monkeypatch.setattr(pred_module, "_model", None)

        prob = predict_failure_probability(90, 90, 5, 5000, 30)
        assert 0 <= prob <= 100

    def test_healthy_service_low_prob(self):
        from predictor import predict_failure_probability
        prob = predict_failure_probability(cpu=20, memory=30, restarts=0, latency=100, error_rate=1)
        assert prob < 50, f"Expected low failure prob for healthy metrics, got {prob}"

    def test_degraded_service_high_prob(self):
        from predictor import predict_failure_probability
        prob = predict_failure_probability(cpu=95, memory=95, restarts=8, latency=9000, error_rate=50)
        assert prob > 50, f"Expected high failure prob for degraded metrics, got {prob}"


# ─── Monitoring ──────────────────────────────────────────────────────────────

class TestMonitor:
    def test_psi_same_distribution(self):
        from monitor import _psi
        arr = np.random.normal(0, 1, 500)
        psi = _psi(arr, arr)
        assert psi < 0.02   # identical distribution → near-zero PSI

    def test_psi_different_distribution(self):
        from monitor import _psi
        base   = np.random.normal(0, 1, 500)
        shifted = np.random.normal(5, 1, 500)   # massively shifted
        psi = _psi(base, shifted)
        assert psi > 0.25   # clear drift

    def test_log_and_load(self, tmp_path, monkeypatch):
        import monitor
        monkeypatch.setattr(monitor, "LOG_PATH", tmp_path / "pred_log.jsonl")
        monitor.log_prediction(
            features={"cpu_pct": 40, "memory_pct": 50},
            probability=30.5,
            service="test-service",
        )
        recs = monitor._load_recent_predictions()
        assert len(recs) == 1
        assert recs[0]["service"] == "test-service"
        assert recs[0]["probability"] == 30.5

    def test_drift_report_no_data(self, tmp_path, monkeypatch):
        import monitor
        monkeypatch.setattr(monitor, "LOG_PATH",      tmp_path / "pred_log.jsonl")
        monkeypatch.setattr(monitor, "BASELINE_PATH", tmp_path / "baseline.json")
        report = monitor.compute_drift_report()
        assert report["n_predictions"] == 0
        assert any("No predictions" in a["message"] for a in report["alerts"])
