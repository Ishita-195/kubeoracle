"""
routers/services.py — Service metrics and ML prediction endpoints
"""
from fastapi import APIRouter
from mock_generator import get_all_metrics
from ml.predictor import predict_failure_probability

router = APIRouter(prefix="/api", tags=["services"])

DEPS = {
    "payment-service":      ["auth-service", "notification-service"],
    "auth-service":         ["user-service"],
    "user-service":         [],
    "notification-service": ["user-service"],
}

REPLICAS = {
    "payment-service": 3,
    "auth-service": 2,
    "user-service": 3,
    "notification-service": 2,
}

RPS = {
    "payment-service": 847,
    "auth-service": 1203,
    "user-service": 562,
    "notification-service": 234,
}

@router.get("/services")
def get_services():
    metrics = get_all_metrics()
    result = []
    for m in metrics:
        prob = predict_failure_probability(
            m["cpu"], m["memory"], m["restarts"], m["latency"], m["error_rate"]
        )
        result.append({
            "id": m["service"],
            "name": m["service"],
            "status": m["status"],
            "cpu": round(m["cpu"], 1),
            "memory": round(m["memory"], 1),
            "restarts": m["restarts"],
            "latency": round(m["latency"], 1),
            "errorRate": round(m["error_rate"], 2),
            "failureProbability": prob,
            "replicas": REPLICAS.get(m["service"], 2),
            "requestsPerSec": RPS.get(m["service"], 100),
            "uptime": "14d 6h",
            "dependencies": DEPS.get(m["service"], []),
        })
    return result
