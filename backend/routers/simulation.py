"""
routers/simulation.py — Trigger and reset failure simulations
"""
from fastapi import APIRouter
from mock_generator import set_simulation

router = APIRouter(prefix="/api", tags=["simulation"])

# NOTE: the static /simulate/reset route must be declared before the
# parameterised /simulate/{service_id} route, otherwise "reset" is captured
# as a service_id and this endpoint becomes unreachable.
@router.post("/simulate/reset")
def reset_simulation():
    set_simulation(None)
    return {"success": True}

@router.post("/simulate/{service_id}")
def trigger_simulation(service_id: str):
    valid = ["payment-service", "auth-service", "user-service", "notification-service"]
    if service_id not in valid:
        return {"success": False, "error": "Unknown service"}
    set_simulation(service_id)
    return {"success": True, "failedService": service_id}
