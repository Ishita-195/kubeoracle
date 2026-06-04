"""
ml_model.py
Trains a lightweight XGBoost classifier to predict K8s service failures.
Uses synthetic training data — no real cluster needed.
"""
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import xgboost as xgb

_model: Pipeline | None = None

def _generate_training_data(n: int = 2000):
    """Synthetic training data mimicking Kubernetes metrics."""
    X, y = [], []
    rng = np.random.default_rng(42)

    for _ in range(n):
        cpu        = rng.uniform(5, 100)
        memory     = rng.uniform(10, 100)
        restarts   = rng.integers(0, 10)
        latency    = rng.uniform(20, 10000)
        error_rate = rng.uniform(0, 100)

        # Label: 1 = failure likely, 0 = healthy
        fail = (
            (cpu > 85 and memory > 80) or
            (restarts >= 3) or
            (error_rate > 20) or
            (latency > 3000 and error_rate > 5)
        )
        X.append([cpu, memory, restarts, latency, error_rate])
        y.append(int(fail))

    return np.array(X), np.array(y)

def get_model() -> Pipeline:
    global _model
    if _model is None:
        X, y = _generate_training_data()
        _model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", xgb.XGBClassifier(
                n_estimators=80,
                max_depth=4,
                learning_rate=0.15,
                use_label_encoder=False,
                eval_metric="logloss",
                verbosity=0,
            )),
        ])
        _model.fit(X, y)
        print("✅ ML model trained on synthetic data.")
    return _model

def predict_failure_probability(cpu: float, memory: float, restarts: int, latency: float, error_rate: float) -> float:
    """Returns failure probability as 0–100."""
    model = get_model()
    features = np.array([[cpu, memory, restarts, latency, error_rate]])
    prob = model.predict_proba(features)[0][1]
    return round(float(prob) * 100, 1)
