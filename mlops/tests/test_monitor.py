"""
Extra unit tests for mlops/monitoring/monitor.py — baseline stats and the
full drift-report path (output drift + feature drift + alert emission).
Basic PSI / logging tests live in test_training.py.
"""
import numpy as np
import pytest


@pytest.fixture
def mon(monkeypatch, tmp_path):
    import monitor
    monkeypatch.setattr(monitor, "LOG_PATH", tmp_path / "preds.jsonl")
    monkeypatch.setattr(monitor, "ALERT_PATH", tmp_path / "alerts.jsonl")
    monkeypatch.setattr(monitor, "BASELINE_PATH", tmp_path / "baseline.json")
    return monitor


def test_compute_and_load_baseline(mon):
    rng = np.random.default_rng(0)
    X = rng.normal(50, 10, size=(200, 2))
    mon.compute_baseline(X, ["cpu_pct", "memory_pct"])
    baseline = mon._load_baseline()
    assert set(baseline["features"]) == {"cpu_pct", "memory_pct"}
    assert "mean" in baseline["features"]["cpu_pct"]


def test_load_baseline_missing_returns_none(mon):
    assert mon._load_baseline() is None


def test_drift_report_flags_output_and_feature_drift(mon):
    # baseline centred at 50; logged values are wildly different -> drift
    mon.compute_baseline(np.full((100, 1), 50.0), ["cpu_pct"])
    for _ in range(40):
        mon.log_prediction(features={"cpu_pct": 5000.0}, probability=85.0, service="svc")

    report = mon.compute_drift_report()
    assert report["n_predictions"] == 40
    assert report["output_drift"]["failure_rate"] == 1.0
    assert "cpu_pct" in report["feature_drift"]
    levels = {a["level"] for a in report["alerts"]}
    assert "warning" in levels        # high failure rate
    assert "critical" in levels       # PSI breach
    assert mon.ALERT_PATH.exists()    # _emit_alert persisted the alerts


def test_drift_report_low_failure_rate_warning(mon):
    for _ in range(30):
        mon.log_prediction(features={"cpu_pct": 50.0}, probability=1.0, service="svc")
    report = mon.compute_drift_report()
    assert report["output_drift"]["failure_rate"] == 0.0
    messages = " ".join(a["message"] for a in report["alerts"])
    assert "low failure rate" in messages.lower()
