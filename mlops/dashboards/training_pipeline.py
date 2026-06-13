"""
mlops/dashboards/training_pipeline.py
Training Pipeline Dashboard

Tracks:
  - Training job status and history
  - Experiment runs
  - Hyperparameter configurations
  - Model artifacts
  - Training logs and metrics
  - Retraining triggers
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

import numpy as np

logger = logging.getLogger("kubeoracle.training_pipeline")

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboards_data"
DASHBOARD_DIR.mkdir(exist_ok=True)

TRAINING_LOG = DASHBOARD_DIR / "training_runs.jsonl"
EXPERIMENT_LOG = DASHBOARD_DIR / "experiments.jsonl"
RETRAINING_LOG = DASHBOARD_DIR / "retraining_triggers.jsonl"


class TrainingPipelineDashboard:
    """
    Tracks model training pipeline and experiment lifecycle.
    """

    def __init__(self):
        self.training_log = TRAINING_LOG
        self.experiment_log = EXPERIMENT_LOG
        self.retraining_log = RETRAINING_LOG

    def log_training_run(
        self,
        run_id: str,
        model_version: str,
        status: str,
        duration_seconds: float,
        train_loss: float,
        val_loss: float,
        metrics: Dict[str, float],
        hyperparameters: Dict[str, Any] = None,
    ) -> None:
        """Log a training run."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "model_version": model_version,
            "status": status,  # "in_progress", "completed", "failed"
            "duration_seconds": round(duration_seconds, 2),
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "metrics": {k: round(v, 4) for k, v in metrics.items()},
            "hyperparameters": hyperparameters or {},
        }
        with open(self.training_log, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(f"Training run logged: {run_id} ({status})")

    def log_experiment(
        self,
        experiment_id: str,
        experiment_name: str,
        description: str,
        status: str = "active",
        runs: List[str] = None,
    ) -> None:
        """Log an experiment."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "description": description,
            "status": status,
            "runs": runs or [],
        }
        with open(self.experiment_log, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(f"Experiment logged: {experiment_name}")

    def log_retraining_trigger(
        self,
        trigger_type: str,
        reason: str,
        confidence: float,
        recommended_action: str,
    ) -> None:
        """Log a retraining trigger event."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "trigger_type": trigger_type,  # "drift", "performance", "scheduled", "manual"
            "reason": reason,
            "confidence": round(confidence, 4),
            "recommended_action": recommended_action,
        }
        with open(self.retraining_log, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.warning(f"Retraining trigger: {trigger_type} - {reason}")

    def get_training_history(self, hours: int = 72) -> Dict[str, Any]:
        """Get training run history."""
        if not self.training_log.exists():
            return {"status": "no_data"}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = []

        with open(self.training_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff_time:
                    records.append(record)

        if not records:
            return {"status": "no_data_in_window"}

        completed = [r for r in records if r["status"] == "completed"]
        failed = [r for r in records if r["status"] == "failed"]

        summary = {
            "window_hours": hours,
            "total_runs": len(records),
            "completed_runs": len(completed),
            "failed_runs": len(failed),
            "success_rate": round(len(completed) / max(len(records), 1), 4),
        }

        if completed:
            val_losses = [r["val_loss"] for r in completed]
            train_losses = [r["train_loss"] for r in completed]
            durations = [r["duration_seconds"] for r in completed]

            summary.update({
                "avg_train_loss": round(np.mean(train_losses), 4),
                "avg_val_loss": round(np.mean(val_losses), 4),
                "best_val_loss": round(np.min(val_losses), 4),
                "avg_duration_seconds": round(np.mean(durations), 2),
                "latest_run": completed[-1],
            })

        if failed:
            summary["failed_runs_sample"] = failed[-3:]

        return summary

    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments."""
        if not self.experiment_log.exists():
            return {"status": "no_data", "experiments": []}

        records = []
        with open(self.experiment_log) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        active_exps = [r for r in records if r["status"] == "active"]
        completed_exps = [r for r in records if r["status"] == "completed"]

        return {
            "total_experiments": len(records),
            "active_experiments": len(active_exps),
            "completed_experiments": len(completed_exps),
            "active": active_exps[-5:] if active_exps else [],
            "recent_completed": completed_exps[-5:] if completed_exps else [],
        }

    def get_retraining_recommendations(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent retraining recommendations."""
        if not self.retraining_log.exists():
            return {"status": "no_data", "recommendations": []}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = []

        with open(self.retraining_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff_time:
                    records.append(record)

        if not records:
            return {"status": "no_recommendations", "window_hours": hours}

        by_type = {}
        for r in records:
            ttype = r["trigger_type"]
            if ttype not in by_type:
                by_type[ttype] = []
            by_type[ttype].append(r)

        return {
            "window_hours": hours,
            "total_recommendations": len(records),
            "by_trigger_type": {
                ttype: {
                    "count": len(runs),
                    "latest": runs[-1],
                    "avg_confidence": round(np.mean([r["confidence"] for r in runs]), 4),
                }
                for ttype, runs in by_type.items()
            },
            "high_confidence_triggers": [
                r for r in records if r["confidence"] >= 0.8
            ],
        }

    def get_model_lineage(self, model_version: str) -> Dict[str, Any]:
        """Get lineage for a specific model version."""
        if not self.training_log.exists():
            return {"status": "no_data"}

        records = []
        with open(self.training_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record["model_version"] == model_version:
                    records.append(record)

        if not records:
            return {"status": "model_not_found", "model_version": model_version}

        completed_runs = [r for r in records if r["status"] == "completed"]
        if not completed_runs:
            return {"status": "no_completed_runs"}

        best_run = min(completed_runs, key=lambda x: x["val_loss"])

        return {
            "model_version": model_version,
            "total_runs": len(records),
            "completed_runs": len(completed_runs),
            "best_run": best_run,
            "all_runs": [
                {
                    "run_id": r["run_id"],
                    "status": r["status"],
                    "val_loss": r["val_loss"],
                    "timestamp": r["ts"],
                }
                for r in records
            ],
        }

    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get overall pipeline health status."""
        summary = {
            "training_status": self._get_training_status(),
            "experiment_status": self._get_experiment_status(),
            "retraining_status": self._get_retraining_status(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        overall_health = "healthy"
        if summary["retraining_status"] == "high_priority_recommendations":
            overall_health = "needs_attention"
        if summary["training_status"] == "recent_failures":
            overall_health = "degraded"

        summary["overall_health"] = overall_health
        return summary

    def _get_training_status(self) -> str:
        if not self.training_log.exists():
            return "no_activity"
        with open(self.training_log) as f:
            lines = f.readlines()
        if not lines:
            return "no_activity"
        recent = json.loads(lines[-1])
        if recent["status"] == "failed":
            return "recent_failures"
        elif recent["status"] == "in_progress":
            return "training_in_progress"
        return "healthy"

    def _get_experiment_status(self) -> str:
        if not self.experiment_log.exists():
            return "no_activity"
        with open(self.experiment_log) as f:
            lines = f.readlines()
        active_count = sum(1 for line in lines if "active" in line)
        return f"{active_count}_active" if active_count > 0 else "no_active_experiments"

    def _get_retraining_status(self) -> str:
        if not self.retraining_log.exists():
            return "no_recommendations"
        cutoff = datetime.utcnow() - timedelta(hours=6)
        with open(self.retraining_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff and record["confidence"] >= 0.9:
                    return "high_priority_recommendations"
        return "no_urgent_recommendations"
