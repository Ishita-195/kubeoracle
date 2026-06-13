"""
backend/routers/mlops.py
MLOps Router — Model metrics, training pipelines, drift detection, and system health
"""
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import sys
import os

router = APIRouter(prefix="/api/mlops", tags=["MLOps"])

# Try to import dashboard modules from mlops/dashboards
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mlops', 'dashboards'))
    from model_performance import ModelPerformanceDashboard
    from data_drift import DataDriftDashboard
    from training_pipeline import TrainingPipelineDashboard
    from system_health import SystemHealthDashboard

    perf_dashboard = ModelPerformanceDashboard()
    drift_dashboard = DataDriftDashboard()
    training_dashboard = TrainingPipelineDashboard()
    health_dashboard = SystemHealthDashboard()
    DASHBOARDS_AVAILABLE = True
except ImportError:
    DASHBOARDS_AVAILABLE = False


# ============================================================================
# Pydantic Models
# ============================================================================

class EvaluationLog(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    confusion_matrix: Any
    model_version: str = "v1.0.0"

class LatencyLog(BaseModel):
    latency_ms: float
    batch_size: int = 1

class FeatureImportanceLog(BaseModel):
    feature_names: List[str]
    importances: List[float]

class DriftDetectionLog(BaseModel):
    feature_name: str
    psi: float
    kl_divergence: float
    reference_stats: Dict[str, float]
    current_stats: Dict[str, float]
    alert_level: str = "info"

class DataQualityLog(BaseModel):
    n_samples: int
    n_missing: int
    n_outliers: int
    schema_violations: int = 0

class TrainingRunLog(BaseModel):
    run_id: str
    model_version: str
    status: str
    duration_seconds: float
    train_loss: float
    val_loss: float
    metrics: Dict[str, float]
    hyperparameters: Optional[Dict[str, Any]] = None

class ResourceMetricsLog(BaseModel):
    cpu_percent: float
    memory_percent: float
    gpu_memory_mb: float = 0
    gpu_util_percent: float = 0
    disk_io_read_mb_s: float = 0
    disk_io_write_mb_s: float = 0
    temperature_celsius: float = 0

class EndpointHealthLog(BaseModel):
    endpoint: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None


# ============================================================================
# Mock Data Generators (fallback when dashboard modules not available)
# ============================================================================

def _mock_performance_summary():
    return {
        "n_evaluations": random.randint(5, 20),
        "accuracy": round(random.uniform(0.88, 0.96), 4),
        "precision": round(random.uniform(0.85, 0.95), 4),
        "recall": round(random.uniform(0.85, 0.95), 4),
        "f1_score": round(random.uniform(0.85, 0.95), 4),
        "auc_roc": round(random.uniform(0.90, 0.99), 4),
        "trend": random.choice(["improving", "stable", "declining"]),
        "latest_version": "v1.0.0",
        "window_hours": 24,
    }

def _mock_latency_stats():
    base = random.uniform(30, 80)
    return {
        "n_samples": random.randint(50, 200),
        "mean_ms": round(base, 2),
        "median_ms": round(base * 0.95, 2),
        "p95_ms": round(base * 1.8, 2),
        "p99_ms": round(base * 2.5, 2),
        "min_ms": round(base * 0.5, 2),
        "max_ms": round(base * 3, 2),
    }

def _mock_drift_summary():
    features = ["cpu_usage", "memory_usage", "response_time", "error_rate", "request_count"]
    return {
        "window_hours": 24,
        "n_checks": random.randint(10, 50),
        "features_monitored": len(features),
        "features": {
            f: {
                "latest_psi": round(random.uniform(0.0, 0.3), 4),
                "mean_psi": round(random.uniform(0.0, 0.2), 4),
                "max_psi": round(random.uniform(0.1, 0.35), 4),
                "drift_status": random.choice(["stable", "warning_drift", "critical_drift"]),
                "latest_alert": random.choice(["info", "warning", "critical"]),
                "mean_shift": round(random.uniform(0, 2), 4),
            }
            for f in features
        },
        "alerts": {"critical": random.randint(0, 2), "warning": random.randint(0, 3), "info": random.randint(1, 5)},
    }

def _mock_training_history():
    completed = random.randint(3, 8)
    failed = random.randint(0, 2)
    return {
        "window_hours": 72,
        "total_runs": completed + failed,
        "completed_runs": completed,
        "failed_runs": failed,
        "success_rate": round(completed / (completed + failed), 4),
        "avg_train_loss": round(random.uniform(0.03, 0.08), 4),
        "avg_val_loss": round(random.uniform(0.05, 0.12), 4),
        "best_val_loss": round(random.uniform(0.04, 0.08), 4),
        "avg_duration_seconds": round(random.uniform(300, 900), 2),
        "latest_run": {
            "run_id": "run_007",
            "model_version": "v1.2.0",
            "status": "completed",
            "val_loss": round(random.uniform(0.05, 0.08), 4),
            "ts": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        },
    }

def _mock_system_health():
    cpu = random.uniform(20, 75)
    mem = random.uniform(30, 80)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "resources": {
            "cpu_health": "healthy" if cpu < 75 else "warning",
            "memory_health": "healthy" if mem < 85 else "critical",
            "temperature_health": "normal",
        },
        "endpoints": {
            "uptime_percent": round(random.uniform(97, 100), 2),
            "status": "healthy",
        },
        "errors": {
            "has_critical_errors": False,
            "error_rate": round(random.uniform(0, 0.5), 2),
            "status": "healthy",
        },
        "overall_status": "healthy",
    }


# ============================================================================
# General
# ============================================================================

@router.get("/health")
def mlops_health():
    return {
        "status": "ok",
        "message": "MLOps dashboards API is running",
        "dashboards_available": DASHBOARDS_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.get("/dashboards")
def list_dashboards():
    return {
        "dashboards": [
            {
                "name": "Model Performance",
                "description": "Accuracy, latency, and feature importance tracking",
                "endpoints": [
                    "POST /model-performance/log-evaluation",
                    "POST /model-performance/log-latency",
                    "POST /model-performance/log-feature-importance",
                    "GET  /model-performance/summary",
                    "GET  /model-performance/latency-stats",
                    "GET  /model-performance/feature-importance",
                ],
            },
            {
                "name": "Data Drift Detection",
                "description": "PSI, KL-divergence, and data quality monitoring",
                "endpoints": [
                    "POST /data-drift/log-detection",
                    "POST /data-drift/log-quality",
                    "GET  /data-drift/summary",
                    "GET  /data-drift/quality",
                    "GET  /data-drift/timeline/{feature}",
                ],
            },
            {
                "name": "Training Pipeline",
                "description": "Training runs, experiments, and retraining triggers",
                "endpoints": [
                    "POST /training/log-run",
                    "GET  /training/history",
                    "GET  /training/experiments",
                    "GET  /training/recommendations",
                    "GET  /training/pipeline-health",
                ],
            },
            {
                "name": "System Health",
                "description": "CPU, GPU, memory, endpoint health, and error logs",
                "endpoints": [
                    "POST /system/log-resources",
                    "POST /system/log-endpoint-health",
                    "GET  /system/resources",
                    "GET  /system/endpoints",
                    "GET  /system/errors",
                    "GET  /system/health",
                ],
            },
        ]
    }


# ============================================================================
# Model Performance Endpoints
# ============================================================================

@router.post("/model-performance/log-evaluation")
def log_evaluation(payload: EvaluationLog):
    if DASHBOARDS_AVAILABLE:
        perf_dashboard.log_evaluation(
            accuracy=payload.accuracy,
            precision=payload.precision,
            recall=payload.recall,
            f1=payload.f1,
            auc_roc=payload.auc_roc,
            confusion_matrix=payload.confusion_matrix,
            model_version=payload.model_version,
        )
    return {"status": "logged", "timestamp": datetime.utcnow().isoformat()}


@router.post("/model-performance/log-latency")
def log_latency(payload: LatencyLog):
    if DASHBOARDS_AVAILABLE:
        perf_dashboard.log_latency(latency_ms=payload.latency_ms, batch_size=payload.batch_size)
    return {"status": "logged"}


@router.post("/model-performance/log-feature-importance")
def log_feature_importance(payload: FeatureImportanceLog):
    if DASHBOARDS_AVAILABLE:
        perf_dashboard.log_feature_importance(
            feature_names=payload.feature_names,
            importances=payload.importances,
        )
    return {"status": "logged"}


@router.get("/model-performance/summary")
def get_performance_summary(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return perf_dashboard.get_performance_summary(hours=hours)
    return _mock_performance_summary()


@router.get("/model-performance/latency-stats")
def get_latency_stats(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return perf_dashboard.get_latency_stats(hours=hours)
    return _mock_latency_stats()


@router.get("/model-performance/feature-importance")
def get_feature_importance():
    if DASHBOARDS_AVAILABLE:
        return perf_dashboard.get_feature_importance()
    features = ["cpu_usage", "memory_usage", "response_time", "error_rate", "request_count"]
    importances = sorted([random.uniform(0.05, 0.35) for _ in features], reverse=True)
    total = sum(importances)
    return {
        "features": [
            {"name": f, "importance": round(v / total, 4)}
            for f, v in zip(features, importances)
        ]
    }


# ============================================================================
# Data Drift Endpoints
# ============================================================================

@router.post("/data-drift/log-detection")
def log_drift_detection(payload: DriftDetectionLog):
    if DASHBOARDS_AVAILABLE:
        drift_dashboard.log_drift_detection(
            feature_name=payload.feature_name,
            psi=payload.psi,
            kl_div=payload.kl_divergence,
            reference_stats=payload.reference_stats,
            current_stats=payload.current_stats,
            alert_level=payload.alert_level,
        )
    return {"status": "logged"}


@router.post("/data-drift/log-quality")
def log_data_quality(payload: DataQualityLog):
    if DASHBOARDS_AVAILABLE:
        drift_dashboard.log_data_quality(
            n_samples=payload.n_samples,
            n_missing=payload.n_missing,
            n_outliers=payload.n_outliers,
            schema_violations=payload.schema_violations,
        )
    return {"status": "logged"}


@router.get("/data-drift/summary")
def get_drift_summary(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return drift_dashboard.get_drift_summary(hours=hours)
    return _mock_drift_summary()


@router.get("/data-drift/quality")
def get_data_quality(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return drift_dashboard.get_data_quality_summary(hours=hours)
    return {
        "window_hours": hours,
        "n_batches": random.randint(5, 20),
        "total_samples": random.randint(5000, 20000),
        "total_missing": random.randint(10, 200),
        "total_outliers": random.randint(5, 100),
        "avg_missing_rate": round(random.uniform(0.005, 0.04), 4),
        "max_missing_rate": round(random.uniform(0.02, 0.08), 4),
        "avg_outlier_rate": round(random.uniform(0.003, 0.02), 4),
        "max_outlier_rate": round(random.uniform(0.01, 0.05), 4),
        "latest_quality": {
            "timestamp": datetime.utcnow().isoformat(),
            "missing_rate": round(random.uniform(0.005, 0.04), 4),
            "outlier_rate": round(random.uniform(0.003, 0.02), 4),
            "status": "healthy",
        },
    }


@router.get("/data-drift/timeline/{feature}")
def get_drift_timeline(feature: str, days: int = 7):
    if DASHBOARDS_AVAILABLE:
        return drift_dashboard.get_feature_drift_timeline(feature=feature, days=days)
    now = datetime.utcnow()
    return {
        "feature": feature,
        "period_days": days,
        "n_observations": days * 4,
        "timeline": [
            {
                "timestamp": (now - timedelta(hours=i * 6)).isoformat(),
                "psi": round(random.uniform(0.02, 0.28), 4),
                "kl_divergence": round(random.uniform(0.01, 0.18), 4),
                "alert_level": random.choice(["info", "info", "info", "warning"]),
                "mean_shift": round(random.uniform(0, 3), 4),
            }
            for i in range(days * 4)
        ],
        "max_psi": round(random.uniform(0.15, 0.3), 4),
        "latest_status": "stable",
    }


# ============================================================================
# Training Pipeline Endpoints
# ============================================================================

@router.post("/training/log-run")
def log_training_run(payload: TrainingRunLog):
    if DASHBOARDS_AVAILABLE:
        training_dashboard.log_training_run(
            run_id=payload.run_id,
            model_version=payload.model_version,
            status=payload.status,
            duration_seconds=payload.duration_seconds,
            train_loss=payload.train_loss,
            val_loss=payload.val_loss,
            metrics=payload.metrics,
            hyperparameters=payload.hyperparameters,
        )
    return {"status": "logged"}


@router.get("/training/history")
def get_training_history(hours: int = 72):
    if DASHBOARDS_AVAILABLE:
        return training_dashboard.get_training_history(hours=hours)
    return _mock_training_history()


@router.get("/training/experiments")
def get_experiments():
    if DASHBOARDS_AVAILABLE:
        return training_dashboard.get_experiment_summary()
    return {
        "total_experiments": random.randint(3, 10),
        "active_experiments": random.randint(1, 3),
        "completed_experiments": random.randint(2, 7),
        "active": [
            {
                "experiment_id": "exp_lr_tuning",
                "experiment_name": "Learning Rate Sweep",
                "description": "Grid search over learning rates",
                "status": "active",
                "runs": ["run_005", "run_006", "run_007"],
                "ts": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            }
        ],
    }


@router.get("/training/recommendations")
def get_retraining_recommendations(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return training_dashboard.get_retraining_recommendations(hours=hours)
    return {
        "window_hours": hours,
        "total_recommendations": random.randint(0, 3),
        "by_trigger_type": {
            "drift": {
                "count": 1,
                "latest": {
                    "trigger_type": "drift",
                    "reason": "Feature PSI exceeded 0.25 threshold",
                    "confidence": 0.87,
                    "recommended_action": "Retrain with last 30 days of data",
                    "ts": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                },
                "avg_confidence": 0.87,
            }
        },
        "high_confidence_triggers": [],
    }


@router.get("/training/pipeline-health")
def get_pipeline_health():
    if DASHBOARDS_AVAILABLE:
        return training_dashboard.get_pipeline_health()
    return {
        "training_status": "healthy",
        "experiment_status": "2_active",
        "retraining_status": "no_urgent_recommendations",
        "overall_health": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# System Health Endpoints
# ============================================================================

@router.post("/system/log-resources")
def log_resources(payload: ResourceMetricsLog):
    if DASHBOARDS_AVAILABLE:
        health_dashboard.log_resource_metrics(
            cpu_percent=payload.cpu_percent,
            memory_percent=payload.memory_percent,
            gpu_memory_mb=payload.gpu_memory_mb,
            gpu_util_percent=payload.gpu_util_percent,
            disk_io_read_mb_s=payload.disk_io_read_mb_s,
            disk_io_write_mb_s=payload.disk_io_write_mb_s,
            temperature_celsius=payload.temperature_celsius,
        )
    return {"status": "logged"}


@router.post("/system/log-endpoint-health")
def log_endpoint_health(payload: EndpointHealthLog):
    if DASHBOARDS_AVAILABLE:
        health_dashboard.log_endpoint_health(
            endpoint=payload.endpoint,
            status_code=payload.status_code,
            response_time_ms=payload.response_time_ms,
            success=payload.success,
            error_message=payload.error_message,
        )
    return {"status": "logged"}


@router.get("/system/resources")
def get_resources(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return health_dashboard.get_resource_summary(hours=hours)
    cpu = random.uniform(25, 70)
    mem = random.uniform(40, 75)
    return {
        "window_hours": hours,
        "n_samples": random.randint(50, 200),
        "cpu": {"mean": round(cpu, 2), "max": round(cpu * 1.3, 2), "min": round(cpu * 0.6, 2), "p95": round(cpu * 1.2, 2), "latest": round(cpu, 2)},
        "memory": {"mean": round(mem, 2), "max": round(mem * 1.2, 2), "min": round(mem * 0.8, 2), "latest": round(mem, 2), "status": "healthy"},
        "gpu_memory_mb": {"mean": round(random.uniform(2000, 6000), 2), "max": round(random.uniform(5000, 8000), 2), "latest": round(random.uniform(2000, 6000), 2)},
        "gpu_utilization": {"mean": round(random.uniform(40, 80), 2), "max": round(random.uniform(70, 95), 2), "latest": round(random.uniform(40, 80), 2)},
        "temperature_celsius": {"mean": 62.5, "max": 71.0, "latest": 63.1, "status": "normal"},
    }


@router.get("/system/endpoints")
def get_endpoint_health(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return health_dashboard.get_endpoint_health(hours=hours)
    endpoints = ["/api/predict", "/api/drift", "/api/mlops/health", "/api/services"]
    return {
        "window_hours": hours,
        "overall_uptime_percent": round(random.uniform(98.5, 100), 2),
        "health_status": "healthy",
        "endpoints": {
            ep: {
                "total_checks": random.randint(50, 200),
                "success_rate": round(random.uniform(0.97, 1.0), 4),
                "uptime_percent": round(random.uniform(98, 100), 2),
                "avg_response_time_ms": round(random.uniform(20, 80), 2),
                "p95_response_time_ms": round(random.uniform(60, 180), 2),
                "max_response_time_ms": round(random.uniform(100, 400), 2),
                "latest_status": "up",
                "latest_response_time_ms": round(random.uniform(20, 80), 2),
            }
            for ep in endpoints
        },
    }


@router.get("/system/errors")
def get_error_summary(hours: int = 24):
    if DASHBOARDS_AVAILABLE:
        return health_dashboard.get_error_summary(hours=hours)
    total = random.randint(0, 5)
    return {
        "window_hours": hours,
        "total_errors": total,
        "by_severity": {"warning": total, "critical": 0, "info": 0},
        "by_type": {"TimeoutError": max(0, total - 1), "OutOfMemory": min(1, total)},
        "critical_errors": [],
        "recent_errors": [],
        "error_rate": round(total / 24, 2),
    }


@router.get("/system/health")
def get_system_health():
    if DASHBOARDS_AVAILABLE:
        return health_dashboard.get_system_health_overall()
    return _mock_system_health()


# ============================================================================
# Summary endpoint (used by the frontend dashboard overview)
# ============================================================================

@router.get("/summary")
def get_mlops_summary():
    perf = _mock_performance_summary() if not DASHBOARDS_AVAILABLE else perf_dashboard.get_performance_summary(hours=24)
    training = _mock_training_history() if not DASHBOARDS_AVAILABLE else training_dashboard.get_training_history(hours=72)
    drift = _mock_drift_summary() if not DASHBOARDS_AVAILABLE else drift_dashboard.get_drift_summary(hours=24)
    system = _mock_system_health() if not DASHBOARDS_AVAILABLE else health_dashboard.get_system_health_overall()

    return {
        "model_accuracy": perf.get("accuracy", 0.92),
        "model_f1": perf.get("f1_score", 0.90),
        "training_success_rate": training.get("success_rate", 0.95),
        "total_training_runs": training.get("total_runs", 0),
        "drift_alerts": drift.get("alerts", {}).get("critical", 0) + drift.get("alerts", {}).get("warning", 0),
        "system_status": system.get("overall_status", "healthy"),
        "timestamp": datetime.utcnow().isoformat(),
    }
