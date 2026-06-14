"""
Extra training tests — the balanced label distribution and cross-validation.
The end-to-end run_training path is exercised by test_pipeline.py.
"""
import pytest


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    import train
    monkeypatch.setattr(train, "DATA_DIR", tmp_path)
    return train


def test_balanced_positive_rate(sandbox):
    _, y = sandbox.generate_synthetic_data(n=2000)
    rate = y.mean()
    assert 0.20 < rate < 0.60, f"expected a balanced dataset, got {rate:.2%}"


def test_cross_validate_returns_scores(sandbox):
    X, y = sandbox.generate_synthetic_data(n=400)
    pipe = sandbox.build_pipeline({"n_estimators": 15, "max_depth": 2, "learning_rate": 0.1})
    cv = sandbox.cross_validate(pipe, X, y, cv=3)
    assert "cv_f1_mean" in cv and "cv_f1_std" in cv
    assert 0.0 <= cv["cv_f1_mean"] <= 1.0
