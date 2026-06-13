"""
mlops/dashboards/model_performance.py
Model Performance Dashboard

Tracks:
  - Model accuracy, precision, recall, F1, AUC-ROC
  - Inference latency (mean, p95, p99)
  - Feature importance scores
  - Evaluation history with trend analysis
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

import numpy as np

logger = logging.getLogger("kubeoracle.model_performance")

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboards_data"
DASHBOARD_DIR.mkdir(exist_ok=True)

PERF_LOG = DASHBOARD_DIR / "model_performance.jsonl"
LATENCY_LOG = DASHBOARD_DIR / "model_latency.jsonl"
FEATURE_LOG = DASHBOARD_DIR / "feature_importance.jsonl"


def create_performance_checkpoint(
    accuracy: float,
    f1: float,
    auc_roc: float,
    model_version: str = "v1.0.0",
) -> Dict[str, Any]:
    """Quick helper to create a performance checkpoint."""
    dashboard = ModelPerformanceDashboard()
    dashboard.log_evaluation(
        accuracy=accuracy,
        precision=f1,
        recall=f1,
        f1=f1,
        auc_roc=auc_roc,
        confusion_matrix=[[0, 0], [0, 0]],
        model_version=model_version,
    )
    return dashboard.get_performance_summary(hours=1)


class ModelPerformanceDashboard:
    """Tracks model evaluation metrics and inference performance."""

    ACCURACY_WARN_THRESHOLD = 0.85
    ACCURACY_CRITICAL_THRESHOLD = 0.75
    LATENCY_WARN_MS = 200
    LATENCY_CRITICAL_MS = 500

    def __init__(self):
        self.perf_log = PERF_LOG
        self.latency_log = LATENCY_LOG
        self.feature_log = FEATURE_LOG

    def log_evaluation(
        self,
        accuracy: float,
        precision: float,
        recall: float,
        f1: float,
        auc_roc: float,
        confusion_matrix: Any,
        model_version: str = "v1.0.0",
    ) -> None:
        """Log a model evaluation result."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "model_version": model_version,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "auc_roc": round(auc_roc, 4),
            "confusion_matrix": confusion_matrix,
        }
        with open(self.perf_log, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Check thresholds
        if accuracy < self.ACCURACY_CRITICAL_THRESHOLD:
            logger.error(f"[CRITICAL] Model accuracy {accuracy:.2%} below critical threshold")
        elif accuracy < self.ACCURACY_WARN_THRESHOLD:
            logger.warning(f"[WARNING] Model accuracy {accuracy:.2%} below warning threshold")

    def log_latency(self, latency_ms: float, batch_size: int = 1) -> None:
        """Log a single inference latency measurement."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "latency_ms": round(latency_ms, 2),
            "batch_size": batch_size,
        }
        with open(self.latency_log, "a") as f:
            f.write(json.dumps(record) + "\n")

    def log_feature_importance(
        self, feature_names: List[str], importances: List[float]
    ) -> None:
        """Log feature importance scores."""
        total = sum(importances) or 1
        record = {
            "ts": datetime.utcnow().isoformat(),
            "features": [
                {"name": n, "importance": round(v / total, 4)}
                for n, v in sorted(
                    zip(feature_names, importances), key=lambda x: -x[1]
                )
            ],
        }
        with open(self.feature_log, "a") as f:
            f.write(json.dumps(record) + "\n")

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get model performance metrics over a time window."""
        if not self.perf_log.exists():
            return {"status": "no_data"}

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        records = []
        with open(self.perf_log) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if datetime.fromisoformat(r["ts"]) >= cutoff:
                    records.append(r)

        if not records:
            return {"status": "no_data_in_window", "window_hours": hours}

        accuracies = [r["accuracy"] for r in records]
        f1s = [r["f1"] for r in records]

        trend = "stable"
        if len(accuracies) >= 2:
            if accuracies[-1] > accuracies[0] + 0.01:
                trend = "improving"
            elif accuracies[-1] < accuracies[0] - 0.01:
                trend = "declining"

        return {
            "n_evaluations": len(records),
            "window_hours": hours,
            "accuracy": round(float(np.mean(accuracies)), 4),
            "precision": round(float(np.mean([r["precision"] for r in records])), 4),
            "recall": round(float(np.mean([r["recall"] for r in records])), 4),
            "f1_score": round(float(np.mean(f1s)), 4),
            "auc_roc": round(float(np.mean([r["auc_roc"] for r in records])), 4),
            "accuracy_min": round(float(np.min(accuracies)), 4),
            "accuracy_max": round(float(np.max(accuracies)), 4),
            "trend": trend,
            "latest_version": records[-1]["model_version"],
        }

    def get_latency_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get inference latency statistics."""
        if not self.latency_log.exists():
            return {"status": "no_data"}

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        latencies = []
        with open(self.latency_log) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if datetime.fromisoformat(r["ts"]) >= cutoff:
                    latencies.append(r["latency_ms"])

        if not latencies:
            return {"status": "no_data_in_window"}

        arr = np.array(latencies)
        return {
            "n_samples": len(latencies),
            "mean_ms": round(float(np.mean(arr)), 2),
            "median_ms": round(float(np.median(arr)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "min_ms": round(float(np.min(arr)), 2),
            "max_ms": round(float(np.max(arr)), 2),
            "std_ms": round(float(np.std(arr)), 2),
        }

    def get_feature_importance(self) -> Dict[str, Any]:
        """Get the most recent feature importance ranking."""
        if not self.feature_log.exists():
            return {"status": "no_data", "features": []}

        last_record = None
        with open(self.feature_log) as f:
            for line in f:
                if line.strip():
                    last_record = json.loads(line)

        if not last_record:
            return {"status": "no_data", "features": []}

        return {"features": last_record["features"], "computed_at": last_record["ts"]}
