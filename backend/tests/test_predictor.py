"""
Unit tests for backend/ml/predictor.py and backend/mock_generator.py.
"""
import ml.predictor as predictor
import mock_generator as mg


# ─── ml.predictor ─────────────────────────────────────────────────────────────

class TestPredictor:
    def test_model_is_cached(self):
        m1 = predictor.get_model()
        m2 = predictor.get_model()
        assert m1 is m2   # second call returns the cached instance

    def test_probability_in_range(self):
        prob = predictor.predict_failure_probability(50, 50, 1, 500, 10)
        assert 0.0 <= prob <= 100.0

    def test_healthy_metrics_low_probability(self):
        prob = predictor.predict_failure_probability(
            cpu=15, memory=25, restarts=0, latency=80, error_rate=0.1
        )
        assert prob < 50

    def test_degraded_metrics_high_probability(self):
        prob = predictor.predict_failure_probability(
            cpu=96, memory=95, restarts=9, latency=9500, error_rate=80
        )
        assert prob > 50

    def test_training_data_shape_and_labels(self):
        X, y = predictor._generate_training_data(n=150)
        assert X.shape == (150, 5)
        assert y.shape == (150,)
        assert set(y.tolist()).issubset({0, 1})


# ─── mock_generator ───────────────────────────────────────────────────────────

class TestMockGenerator:
    def teardown_method(self):
        mg.set_simulation(None)   # always reset global state

    def test_generate_metric_keys(self):
        m = mg.generate_metric("payment-service")
        for k in ["service", "cpu", "memory", "restarts", "latency", "error_rate", "status"]:
            assert k in m

    def test_get_all_metrics_covers_every_service(self):
        metrics = mg.get_all_metrics()
        assert {m["service"] for m in metrics} == set(mg.SERVICES)

    def test_simulation_marks_service_failed(self):
        mg.set_simulation("payment-service")
        m = mg.generate_metric("payment-service")
        assert m["status"] == "failed"
        assert m["cpu"] <= 99 and m["memory"] <= 99

    def test_simulation_cascade_marks_dependents_critical(self):
        mg.set_simulation("payment-service")
        m = mg.generate_metric("auth-service")
        assert m["status"] == "critical"

    def test_reset_returns_to_baseline_status(self):
        mg.set_simulation("payment-service")
        mg.set_simulation(None)
        m = mg.generate_metric("payment-service")
        assert m["status"] in ("healthy", "warning")
