"""
mock_generator.py
Generates synthetic Kubernetes-style metrics for demo purposes.
No real Minikube connection needed for the demo.
"""
import random
import time
from datetime import datetime

SERVICES = ["payment-service", "auth-service", "user-service", "notification-service"]

BASE_METRICS = {
    "payment-service":    {"cpu": 34, "memory": 52, "restarts": 0, "latency": 120, "error_rate": 0.2},
    "auth-service":       {"cpu": 72, "memory": 68, "restarts": 2, "latency": 340, "error_rate": 1.8},
    "user-service":       {"cpu": 28, "memory": 41, "restarts": 0, "latency":  89, "error_rate": 0.1},
    "notification-service":{"cpu": 18, "memory": 35,"restarts": 0, "latency":  67, "error_rate": 0.05},
}

_simulation_state: dict = {"active": False, "failed": None}

def set_simulation(service: str | None):
    _simulation_state["active"] = service is not None
    _simulation_state["failed"] = service

def generate_metric(service: str) -> dict:
    base = BASE_METRICS[service]
    jitter = lambda v, scale=0.1: v + random.gauss(0, v * scale)

    if _simulation_state["active"] and _simulation_state["failed"] == service:
        # Failed service — spike everything
        return {
            "service": service,
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": min(99, jitter(95, 0.02)),
            "memory": min(99, jitter(97, 0.01)),
            "restarts": base["restarts"] + random.randint(3, 8),
            "latency": jitter(9500, 0.1),
            "error_rate": jitter(94, 0.05),
            "status": "failed",
        }

    if _simulation_state["active"] and service in ("auth-service", "notification-service"):
        # Affected by cascade
        return {
            "service": service,
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": min(95, jitter(base["cpu"] + 28, 0.05)),
            "memory": min(95, jitter(base["memory"] + 18, 0.05)),
            "restarts": base["restarts"],
            "latency": jitter(base["latency"] * 7, 0.15),
            "error_rate": jitter(base["error_rate"] * 12, 0.1),
            "status": "critical",
        }

    return {
        "service": service,
        "timestamp": datetime.utcnow().isoformat(),
        "cpu": max(0, jitter(base["cpu"])),
        "memory": max(0, jitter(base["memory"])),
        "restarts": base["restarts"],
        "latency": max(10, jitter(base["latency"])),
        "error_rate": max(0, jitter(base["error_rate"])),
        "status": "warning" if base["cpu"] > 65 else "healthy",
    }

def get_all_metrics() -> list[dict]:
    return [generate_metric(s) for s in SERVICES]
