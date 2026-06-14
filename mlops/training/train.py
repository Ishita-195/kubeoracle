"""
mlops/training/train.py
KubeOracle MLOps Training Pipeline

Responsible for:
- Generating / loading training data
- Running experiments with MLflow tracking
- Training, evaluating, and versioning models
- Registering best model to the Model Registry

Usage:
    python train.py                  # full training run
    python train.py --n-samples 5000 # larger synthetic dataset
    python train.py --experiment dev  # custom MLflow experiment name
"""

import argparse
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "mlops" / "data"
MODEL_DIR = ROOT / "mlops" / "model_registry" / "artifacts"
REPORT_DIR = ROOT / "mlops" / "model_registry" / "reports"

for d in [DATA_DIR, MODEL_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Feature names ────────────────────────────────────────────────────────────
FEATURE_NAMES = ["cpu_pct", "memory_pct", "restarts", "latency_ms", "error_rate_pct"]
TARGET_NAME = "failure"

# ─── Hyperparameter grid ─────────────────────────────────────────────────────
PARAM_GRID = [
    {"n_estimators": 80,  "max_depth": 4, "learning_rate": 0.15},
    {"n_estimators": 120, "max_depth": 5, "learning_rate": 0.10},
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05},
]


# ─────────────────────────────────────────────────────────────────────────────
# Data generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_data(n: int = 3000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic K8s metrics with realistic failure patterns.
    Saves a versioned snapshot to DATA_DIR for lineage tracking.
    """
    rng = np.random.default_rng(seed)
    X, y = [], []

    for _ in range(n):
        cpu        = rng.uniform(5, 100)
        memory     = rng.uniform(10, 100)
        restarts   = int(rng.integers(0, 12))
        latency    = rng.uniform(20, 12000)
        error_rate = rng.uniform(0, 100)

        # Multi-condition failure label — tuned to produce a balanced dataset
        # (~37% positives) so the classifier learns a real decision boundary
        # rather than a near-degenerate "always fail" rule.
        fail = (
            (cpu > 88 and memory > 85) or            # CPU and memory both critical
            (restarts >= 10) or                      # severe crash-looping
            (error_rate > 85) or                     # very high error rate
            (latency > 9000 and error_rate > 55)     # severe latency with errors
        )
        X.append([cpu, memory, restarts, latency, error_rate])
        y.append(int(fail))

    X_arr, y_arr = np.array(X), np.array(y)

    # Save versioned snapshot
    version = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    snap = {"version": version, "n_samples": n, "seed": seed,
            "features": FEATURE_NAMES, "X": X_arr.tolist(), "y": y_arr.tolist()}
    snap_path = DATA_DIR / f"dataset_{version}.json"
    with open(snap_path, "w") as f:
        json.dump(snap, f)
    print(f"📦 Dataset snapshot saved → {snap_path}")
    return X_arr, y_arr


# ─────────────────────────────────────────────────────────────────────────────
# Model building
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline(params: dict) -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", xgb.XGBClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            use_label_encoder=False,
            eval_metric="logloss",
            verbosity=0,
            random_state=42,
        )),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(pipeline: Pipeline, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    y_pred  = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    return {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba), 4),
        "report":    classification_report(y_test, y_pred),
    }


def cross_validate(pipeline: Pipeline, X: np.ndarray, y: np.ndarray, cv: int = 5) -> dict:
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    fold_scores = []
    for train_idx, val_idx in skf.split(X, y):
        pipeline.fit(X[train_idx], y[train_idx])
        preds = pipeline.predict(X[val_idx])
        fold_scores.append(f1_score(y[val_idx], preds, zero_division=0))
    return {
        "cv_f1_mean": round(float(np.mean(fold_scores)), 4),
        "cv_f1_std":  round(float(np.std(fold_scores)), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main training loop
# ─────────────────────────────────────────────────────────────────────────────

def run_training(experiment_name: str = "kubeoracle-failure-prediction",
                 n_samples: int = 3000) -> dict:
    mlflow.set_experiment(experiment_name)
    print(f"\n🔬 Experiment: {experiment_name}")

    X, y = generate_synthetic_data(n=n_samples)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"📊 Train={len(X_train)}  Test={len(X_test)}  Positive rate={y.mean():.2%}")

    best_run = None
    best_auc = -1.0

    for idx, params in enumerate(PARAM_GRID):
        run_id = str(uuid.uuid4())[:8]
        print(f"\n▶ Trial {idx+1}/{len(PARAM_GRID)} — params={params}")

        with mlflow.start_run(run_name=f"trial_{idx+1}_{run_id}"):
            mlflow.log_params(params)
            mlflow.log_param("n_samples", n_samples)
            mlflow.log_param("feature_names", ",".join(FEATURE_NAMES))

            pipe = build_pipeline(params)

            t0 = time.time()
            pipe.fit(X_train, y_train)
            train_time = round(time.time() - t0, 2)

            metrics = evaluate(pipe, X_test, y_test)
            cv      = cross_validate(build_pipeline(params), X_train, y_train)

            mlflow.log_metric("accuracy",    metrics["accuracy"])
            mlflow.log_metric("precision",   metrics["precision"])
            mlflow.log_metric("recall",      metrics["recall"])
            mlflow.log_metric("f1",          metrics["f1"])
            mlflow.log_metric("roc_auc",     metrics["roc_auc"])
            mlflow.log_metric("cv_f1_mean",  cv["cv_f1_mean"])
            mlflow.log_metric("cv_f1_std",   cv["cv_f1_std"])
            mlflow.log_metric("train_time_s", train_time)

            mlflow.sklearn.log_model(pipe, artifact_path="model")

            print(f"  AUC={metrics['roc_auc']}  F1={metrics['f1']}  "
                  f"CV-F1={cv['cv_f1_mean']}±{cv['cv_f1_std']}")

            if metrics["roc_auc"] > best_auc:
                best_auc  = metrics["roc_auc"]
                best_run  = {
                    "run_id":       mlflow.active_run().info.run_id,
                    "params":       params,
                    "metrics":      {**metrics, **cv},
                    "train_time_s": train_time,
                    "model":        pipe,
                }

    print(f"\n🏆 Best model — AUC={best_auc}  params={best_run['params']}")
    _register_best_model(best_run)
    return best_run


# ─────────────────────────────────────────────────────────────────────────────
# Model registration (local + MLflow)
# ─────────────────────────────────────────────────────────────────────────────

def _register_best_model(run_info: dict) -> None:
    import pickle

    version   = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    pipe_path = MODEL_DIR / f"model_{version}.pkl"

    with open(pipe_path, "wb") as f:
        pickle.dump(run_info["model"], f)

    # Symlink "latest" for the serving layer
    latest = MODEL_DIR / "model_latest.pkl"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(pipe_path.name)

    # Write metadata card
    meta = {
        "version":      version,
        "mlflow_run_id": run_info["run_id"],
        "params":       run_info["params"],
        "metrics":      {k: v for k, v in run_info["metrics"].items() if k != "report"},
        "features":     FEATURE_NAMES,
        "target":       TARGET_NAME,
        "registered_at": datetime.utcnow().isoformat(),
    }
    meta_path = MODEL_DIR / f"model_{version}_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # Classification report
    report_path = REPORT_DIR / f"eval_{version}.txt"
    with open(report_path, "w") as f:
        f.write(run_info["metrics"]["report"])

    print(f"\n✅ Model saved    → {pipe_path}")
    print(f"✅ Metadata card  → {meta_path}")
    print(f"✅ Eval report    → {report_path}")
    print(f"✅ Symlink latest → {latest}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KubeOracle MLOps training pipeline")
    parser.add_argument("--n-samples",  type=int, default=3000,  help="Synthetic dataset size")
    parser.add_argument("--experiment", type=str, default="kubeoracle-failure-prediction",
                        help="MLflow experiment name")
    args = parser.parse_args()

    result = run_training(experiment_name=args.experiment, n_samples=args.n_samples)
    print("\n🎉 Training complete.")
