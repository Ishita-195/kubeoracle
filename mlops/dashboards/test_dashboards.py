"""
mlops/dashboards/test_dashboards.py
Integration tests for all MLOps dashboards

Run with: python -m pytest mlops/dashboards/test_dashboards.py -v
Or standalone: python mlops/dashboards/test_dashboards.py
"""

import sys
import logging
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dashboard_tests")

from model_performance import ModelPerformanceDashboard
from data_drift import DataDriftDashboard
from training_pipeline import TrainingPipelineDashboard
from system_health import SystemHealthDashboard


class TestDashboards:

    def __init__(self):
        self.test_results = {"passed": [], "failed": [], "errors": []}

    def test_model_performance_dashboard(self) -> bool:
        logger.info("Testing Model Performance Dashboard...")
        try:
            dashboard = ModelPerformanceDashboard()
            dashboard.log_evaluation(
                accuracy=0.92, precision=0.89, recall=0.91, f1=0.90,
                auc_roc=0.94, confusion_matrix=[[450, 50], [40, 460]], model_version="v1.0.0"
            )
            dashboard.log_latency(latency_ms=45.2, batch_size=32)
            dashboard.log_latency(latency_ms=42.8, batch_size=32)
            dashboard.log_feature_importance(
                ["cpu_usage", "memory_usage", "response_time", "error_rate", "request_count"],
                [0.28, 0.25, 0.22, 0.15, 0.10]
            )
            summary = dashboard.get_performance_summary(hours=1)
            assert summary["n_evaluations"] >= 1
            assert "accuracy" in summary
            assert "f1_score" in summary
            logger.info("✅ Model Performance Dashboard: PASSED")
            self.test_results["passed"].append("model_performance_dashboard")
            return True
        except Exception as e:
            logger.error(f"❌ Model Performance Dashboard: FAILED - {e}")
            self.test_results["errors"].append(("model_performance_dashboard", str(e)))
            return False

    def test_data_drift_dashboard(self) -> bool:
        logger.info("Testing Data Drift Dashboard...")
        try:
            dashboard = DataDriftDashboard()
            dashboard.log_drift_detection(
                feature_name="cpu_usage", psi=0.08, kl_div=0.05,
                reference_stats={"mean": 50.0, "std": 15.0},
                current_stats={"mean": 52.3, "std": 16.2}, alert_level="info"
            )
            dashboard.log_drift_detection(
                feature_name="memory_usage", psi=0.18, kl_div=0.12,
                reference_stats={"mean": 60.0, "std": 20.0},
                current_stats={"mean": 68.5, "std": 22.3}, alert_level="warning"
            )
            dashboard.log_data_quality(n_samples=1000, n_missing=15, n_outliers=8, schema_violations=0)
            drift_summary = dashboard.get_drift_summary(hours=1)
            assert drift_summary["features_monitored"] >= 2
            assert "alerts" in drift_summary
            quality_summary = dashboard.get_data_quality_summary(hours=1)
            assert quality_summary["total_samples"] == 1000
            logger.info("✅ Data Drift Dashboard: PASSED")
            self.test_results["passed"].append("data_drift_dashboard")
            return True
        except Exception as e:
            logger.error(f"❌ Data Drift Dashboard: FAILED - {e}")
            self.test_results["errors"].append(("data_drift_dashboard", str(e)))
            return False

    def test_training_pipeline_dashboard(self) -> bool:
        logger.info("Testing Training Pipeline Dashboard...")
        try:
            dashboard = TrainingPipelineDashboard()
            dashboard.log_training_run(
                run_id="run_001", model_version="v1.0.0", status="completed",
                duration_seconds=450.5, train_loss=0.045, val_loss=0.062,
                metrics={"accuracy": 0.92, "f1": 0.90}, hyperparameters={"lr": 0.001, "batch_size": 32}
            )
            dashboard.log_training_run(
                run_id="run_002", model_version="v1.0.0", status="completed",
                duration_seconds=480.2, train_loss=0.038, val_loss=0.055,
                metrics={"accuracy": 0.93, "f1": 0.92}, hyperparameters={"lr": 0.0005, "batch_size": 32}
            )
            dashboard.log_experiment(
                experiment_id="exp_lr_tuning", experiment_name="Learning Rate Tuning",
                description="Testing different learning rates", status="completed",
                runs=["run_001", "run_002"]
            )
            dashboard.log_retraining_trigger(
                trigger_type="drift", reason="Feature PSI exceeded threshold",
                confidence=0.85, recommended_action="Retrain with latest data"
            )
            history = dashboard.get_training_history(hours=1)
            assert history["total_runs"] >= 2
            assert history["completed_runs"] >= 2
            experiments = dashboard.get_experiment_summary()
            assert experiments["total_experiments"] >= 1
            recommendations = dashboard.get_retraining_recommendations(hours=1)
            assert recommendations["total_recommendations"] >= 1
            health = dashboard.get_pipeline_health()
            assert "overall_health" in health
            logger.info("✅ Training Pipeline Dashboard: PASSED")
            self.test_results["passed"].append("training_pipeline_dashboard")
            return True
        except Exception as e:
            logger.error(f"❌ Training Pipeline Dashboard: FAILED - {e}")
            self.test_results["errors"].append(("training_pipeline_dashboard", str(e)))
            return False

    def test_system_health_dashboard(self) -> bool:
        logger.info("Testing System Health Dashboard...")
        try:
            dashboard = SystemHealthDashboard()
            for _ in range(5):
                dashboard.log_resource_metrics(
                    cpu_percent=np.random.uniform(20, 70),
                    memory_percent=np.random.uniform(30, 80),
                    gpu_memory_mb=np.random.uniform(1000, 8000),
                    gpu_util_percent=np.random.uniform(10, 90),
                    disk_io_read_mb_s=np.random.uniform(0, 100),
                    disk_io_write_mb_s=np.random.uniform(0, 100),
                    temperature_celsius=np.random.uniform(50, 75)
                )
            dashboard.log_endpoint_health(endpoint="/api/predict", status_code=200, response_time_ms=45.2, success=True)
            dashboard.log_endpoint_health(endpoint="/api/drift", status_code=200, response_time_ms=32.1, success=True)
            dashboard.log_system_error(
                error_type="OutOfMemory", error_message="Insufficient GPU memory for batch",
                severity="warning", component="predictor"
            )
            resources = dashboard.get_resource_summary(hours=1)
            assert "cpu" in resources
            assert "memory" in resources
            assert resources["n_samples"] >= 5
            endpoints = dashboard.get_endpoint_health(hours=1)
            assert len(endpoints["endpoints"]) >= 2
            errors = dashboard.get_error_summary(hours=1)
            assert errors["total_errors"] >= 1
            overall = dashboard.get_system_health_overall()
            assert "overall_status" in overall
            logger.info("✅ System Health Dashboard: PASSED")
            self.test_results["passed"].append("system_health_dashboard")
            return True
        except Exception as e:
            logger.error(f"❌ System Health Dashboard: FAILED - {e}")
            self.test_results["errors"].append(("system_health_dashboard", str(e)))
            return False

    def run_all_tests(self) -> bool:
        logger.info("=" * 60)
        logger.info("🧪 Starting MLOps Dashboard Test Suite")
        logger.info("=" * 60)
        all_passed = True
        all_passed &= self.test_model_performance_dashboard()
        all_passed &= self.test_data_drift_dashboard()
        all_passed &= self.test_training_pipeline_dashboard()
        all_passed &= self.test_system_health_dashboard()
        logger.info("=" * 60)
        logger.info("📊 Test Summary")
        logger.info("=" * 60)
        logger.info(f"✅ Passed: {len(self.test_results['passed'])}")
        logger.info(f"❌ Failed: {len(self.test_results['failed'])}")
        logger.info(f"⚠️  Errors: {len(self.test_results['errors'])}")
        if self.test_results["errors"]:
            for test_name, error in self.test_results["errors"]:
                logger.error(f"  {test_name}: {error}")
        logger.info("=" * 60)
        return all_passed


if __name__ == "__main__":
    tester = TestDashboards()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
