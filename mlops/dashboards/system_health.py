"""
mlops/dashboards/system_health.py
System & Infrastructure Health Dashboard

Tracks:
  - GPU/CPU utilization
  - Memory usage
  - Disk I/O
  - Model serving latency
  - API endpoint health
  - Resource allocation efficiency
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import numpy as np

logger = logging.getLogger("kubeoracle.system_health")

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboards_data"
DASHBOARD_DIR.mkdir(exist_ok=True)

RESOURCE_LOG = DASHBOARD_DIR / "resource_metrics.jsonl"
ENDPOINT_LOG = DASHBOARD_DIR / "endpoint_health.jsonl"
ERROR_LOG = DASHBOARD_DIR / "system_errors.jsonl"


class SystemHealthDashboard:
    """
    Monitors system resources and service health.
    """

    def __init__(self):
        self.resource_log = RESOURCE_LOG
        self.endpoint_log = ENDPOINT_LOG
        self.error_log = ERROR_LOG

    def log_resource_metrics(
        self,
        cpu_percent: float,
        memory_percent: float,
        gpu_memory_mb: float = 0,
        gpu_util_percent: float = 0,
        disk_io_read_mb_s: float = 0,
        disk_io_write_mb_s: float = 0,
        temperature_celsius: float = 0,
    ) -> None:
        """Log system resource metrics."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "gpu_memory_mb": round(gpu_memory_mb, 2),
            "gpu_util_percent": round(gpu_util_percent, 2),
            "disk_io_read_mb_s": round(disk_io_read_mb_s, 2),
            "disk_io_write_mb_s": round(disk_io_write_mb_s, 2),
            "temperature_celsius": round(temperature_celsius, 2),
        }
        with open(self.resource_log, "a") as f:
            f.write(json.dumps(record) + "\n")

    def log_endpoint_health(
        self,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        success: bool,
        error_message: str = None,
    ) -> None:
        """Log API endpoint health check."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 2),
            "success": success,
            "error_message": error_message,
        }
        with open(self.endpoint_log, "a") as f:
            f.write(json.dumps(record) + "\n")

    def log_system_error(
        self,
        error_type: str,
        error_message: str,
        severity: str,  # "info", "warning", "critical"
        component: str = "unknown",
        traceback: str = None,
    ) -> None:
        """Log system error."""
        record = {
            "ts": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "severity": severity,
            "component": component,
            "traceback": traceback,
        }
        with open(self.error_log, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.error(f"[{severity}] {component}: {error_message}")

    def get_resource_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get resource utilization summary."""
        if not self.resource_log.exists():
            return {"status": "no_data"}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = []

        with open(self.resource_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff_time:
                    records.append(record)

        if not records:
            return {"status": "no_data_in_window"}

        cpu = np.array([r["cpu_percent"] for r in records])
        memory = np.array([r["memory_percent"] for r in records])
        gpu_mem = np.array([r["gpu_memory_mb"] for r in records])
        gpu_util = np.array([r["gpu_util_percent"] for r in records])

        return {
            "window_hours": hours,
            "n_samples": len(records),
            "cpu": {
                "mean": round(np.mean(cpu), 2),
                "max": round(np.max(cpu), 2),
                "min": round(np.min(cpu), 2),
                "std": round(np.std(cpu), 2),
                "p95": round(np.percentile(cpu, 95), 2),
                "latest": records[-1]["cpu_percent"],
            },
            "memory": {
                "mean": round(np.mean(memory), 2),
                "max": round(np.max(memory), 2),
                "min": round(np.min(memory), 2),
                "latest": records[-1]["memory_percent"],
                "status": "critical" if records[-1]["memory_percent"] > 90 else "healthy",
            },
            "gpu_memory_mb": {
                "mean": round(np.mean(gpu_mem), 2),
                "max": round(np.max(gpu_mem), 2),
                "latest": records[-1]["gpu_memory_mb"],
            },
            "gpu_utilization": {
                "mean": round(np.mean(gpu_util), 2),
                "max": round(np.max(gpu_util), 2),
                "latest": records[-1]["gpu_util_percent"],
            },
            "temperature_celsius": {
                "mean": round(np.mean([r["temperature_celsius"] for r in records]), 2),
                "max": round(max(r["temperature_celsius"] for r in records), 2),
                "latest": records[-1]["temperature_celsius"],
                "status": "warning" if records[-1]["temperature_celsius"] > 80 else "normal",
            },
        }

    def get_endpoint_health(self, hours: int = 24) -> Dict[str, Any]:
        """Get endpoint health status."""
        if not self.endpoint_log.exists():
            return {"status": "no_data", "endpoints": {}}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = []

        with open(self.endpoint_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff_time:
                    records.append(record)

        if not records:
            return {"status": "no_data_in_window"}

        by_endpoint = {}
        for record in records:
            ep = record["endpoint"]
            if ep not in by_endpoint:
                by_endpoint[ep] = []
            by_endpoint[ep].append(record)

        endpoints = {}
        for ep, ep_records in by_endpoint.items():
            success_count = sum(1 for r in ep_records if r["success"])
            response_times = [r["response_time_ms"] for r in ep_records]

            endpoints[ep] = {
                "total_checks": len(ep_records),
                "success_rate": round(success_count / len(ep_records), 4),
                "uptime_percent": round(100 * success_count / len(ep_records), 2),
                "avg_response_time_ms": round(np.mean(response_times), 2),
                "p95_response_time_ms": round(np.percentile(response_times, 95), 2),
                "max_response_time_ms": round(np.max(response_times), 2),
                "latest_status": "up" if ep_records[-1]["success"] else "down",
                "latest_response_time_ms": ep_records[-1]["response_time_ms"],
            }

        overall_uptime = round(
            np.mean([v["uptime_percent"] for v in endpoints.values()]), 2
        )

        return {
            "window_hours": hours,
            "overall_uptime_percent": overall_uptime,
            "endpoints": endpoints,
            "health_status": "healthy" if overall_uptime > 95 else "degraded",
        }

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary."""
        if not self.error_log.exists():
            return {"status": "no_errors"}

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        records = []

        with open(self.error_log) as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                ts = datetime.fromisoformat(record["ts"])
                if ts >= cutoff_time:
                    records.append(record)

        if not records:
            return {"status": "no_errors_in_window", "window_hours": hours}

        by_severity = {}
        by_type = {}

        for record in records:
            sev = record["severity"]
            etype = record["error_type"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(record)

        critical_errors = [r for r in records if r["severity"] == "critical"]

        return {
            "window_hours": hours,
            "total_errors": len(records),
            "by_severity": by_severity,
            "by_type": {etype: len(errs) for etype, errs in by_type.items()},
            "critical_errors": critical_errors[-5:] if critical_errors else [],
            "recent_errors": records[-5:],
            "error_rate": round(len(records) / 24, 2),
        }

    def get_system_health_overall(self) -> Dict[str, Any]:
        """Get overall system health status."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "resources": self._assess_resource_health(),
            "endpoints": self._assess_endpoint_health(),
            "errors": self._assess_error_health(),
            "overall_status": self._compute_overall_status(),
        }

    def _assess_resource_health(self) -> Dict[str, Any]:
        summary = self.get_resource_summary(hours=1)
        if summary.get("status") == "no_data":
            return {"status": "unknown"}
        cpu_health = "healthy"
        if summary["cpu"]["latest"] > 90:
            cpu_health = "critical"
        elif summary["cpu"]["latest"] > 75:
            cpu_health = "warning"
        return {
            "cpu_health": cpu_health,
            "memory_health": summary["memory"]["status"],
            "temperature_health": summary["temperature_celsius"]["status"],
        }

    def _assess_endpoint_health(self) -> Dict[str, Any]:
        health = self.get_endpoint_health(hours=1)
        if health.get("status") == "no_data":
            return {"status": "unknown"}
        return {
            "uptime_percent": health["overall_uptime_percent"],
            "status": "healthy" if health["overall_uptime_percent"] > 99 else "degraded",
        }

    def _assess_error_health(self) -> Dict[str, Any]:
        summary = self.get_error_summary(hours=1)
        critical_count = summary.get("by_severity", {}).get("critical", 0)
        return {
            "has_critical_errors": critical_count > 0,
            "error_rate": summary.get("error_rate", 0),
            "status": "critical" if critical_count > 0 else "healthy",
        }

    def _compute_overall_status(self) -> str:
        resource_status = self._assess_resource_health()
        endpoint_status = self._assess_endpoint_health()
        error_status = self._assess_error_health()

        if (
            error_status.get("has_critical_errors")
            or resource_status.get("cpu_health") == "critical"
            or endpoint_status.get("status") == "degraded"
        ):
            return "degraded"

        if (
            resource_status.get("cpu_health") == "warning"
            or resource_status.get("memory_health") == "warning"
        ):
            return "warning"

        return "healthy"
