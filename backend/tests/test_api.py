"""
Integration tests for the FastAPI backend, driven through TestClient.

DASHBOARDS_AVAILABLE is False in this environment (the Dash dashboard
package is a stub), so every /api/mlops endpoint exercises its mock branch.
"""
import pytest


# ─── Core app ─────────────────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"].startswith("KubeOracle")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ─── services / simulation ────────────────────────────────────────────────────

def test_services_endpoint(client):
    r = client.get("/api/services")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    sample = data[0]
    for key in ["id", "status", "cpu", "failureProbability", "dependencies"]:
        assert key in sample
    assert 0 <= sample["failureProbability"] <= 100


def test_simulate_valid_then_reset(client):
    r = client.post("/api/simulate/payment-service")
    assert r.json() == {"success": True, "failedService": "payment-service"}
    # the simulated service should now report as failed
    failed = [s for s in client.get("/api/services").json() if s["id"] == "payment-service"][0]
    assert failed["status"] == "failed"
    assert client.post("/api/simulate/reset").json() == {"success": True}


def test_simulate_unknown_service(client):
    r = client.post("/api/simulate/does-not-exist")
    assert r.json()["success"] is False


# ─── insights ─────────────────────────────────────────────────────────────────

def test_insights_mock_fallback(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    data = client.get("/api/insights").json()
    assert len(data) == 3
    assert all(i["source"] == "mock" for i in data)


def _fake_llm_response(content):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    return _Resp()


def test_insights_openrouter_success(client, monkeypatch):
    import routers.insights as ins
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    payload = '```json\n[{"id":"i1","title":"t","description":"d","action":"a",' \
              '"severity":"info","confidence":90,"source":"ai"}]\n```'
    monkeypatch.setattr(ins.httpx, "post", lambda *a, **k: _fake_llm_response(payload))
    data = client.get("/api/insights").json()
    assert data[0]["source"] == "ai"


def test_insights_groq_branch(client, monkeypatch):
    import routers.insights as ins
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    payload = '[{"id":"i1","title":"t","description":"d","action":"a",' \
              '"severity":"info","confidence":80,"source":"ai"}]'
    monkeypatch.setattr(ins.httpx, "post", lambda *a, **k: _fake_llm_response(payload))
    data = client.get("/api/insights").json()
    assert data[0]["source"] == "ai"


def test_insights_handles_call_exception(client, monkeypatch):
    import routers.insights as ins
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(ins.httpx, "post", _boom)
    # all providers fail -> falls back to mock without raising
    data = client.get("/api/insights").json()
    assert all(i["source"] == "mock" for i in data)


def test_alerts(client):
    data = client.get("/api/alerts").json()
    assert len(data) == 3
    assert {a["id"] for a in data} == {"a1", "a2", "a3"}


# ─── mlops router (mock branches) ─────────────────────────────────────────────

GET_ENDPOINTS = [
    "/api/mlops/health",
    "/api/mlops/dashboards",
    "/api/mlops/model-performance/summary",
    "/api/mlops/model-performance/latency-stats",
    "/api/mlops/model-performance/feature-importance",
    "/api/mlops/data-drift/summary",
    "/api/mlops/data-drift/quality",
    "/api/mlops/data-drift/timeline/cpu_usage",
    "/api/mlops/training/history",
    "/api/mlops/training/experiments",
    "/api/mlops/training/recommendations",
    "/api/mlops/training/pipeline-health",
    "/api/mlops/system/resources",
    "/api/mlops/system/endpoints",
    "/api/mlops/system/errors",
    "/api/mlops/system/health",
    "/api/mlops/summary",
]


@pytest.mark.parametrize("path", GET_ENDPOINTS)
def test_mlops_get_endpoints(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_mlops_health_reports_dashboards_unavailable(client):
    body = client.get("/api/mlops/health").json()
    assert body["status"] == "ok"
    assert body["dashboards_available"] is False


POST_CASES = [
    ("/api/mlops/model-performance/log-evaluation",
     {"accuracy": 0.9, "precision": 0.9, "recall": 0.9, "f1": 0.9,
      "auc_roc": 0.95, "confusion_matrix": [[10, 1], [2, 9]]}),
    ("/api/mlops/model-performance/log-latency", {"latency_ms": 42.0, "batch_size": 4}),
    ("/api/mlops/model-performance/log-feature-importance",
     {"feature_names": ["cpu", "mem"], "importances": [0.6, 0.4]}),
    ("/api/mlops/data-drift/log-detection",
     {"feature_name": "cpu", "psi": 0.1, "kl_divergence": 0.05,
      "reference_stats": {"mean": 1.0}, "current_stats": {"mean": 1.2}}),
    ("/api/mlops/data-drift/log-quality",
     {"n_samples": 1000, "n_missing": 5, "n_outliers": 3}),
    ("/api/mlops/training/log-run",
     {"run_id": "r1", "model_version": "v1", "status": "completed",
      "duration_seconds": 12.0, "train_loss": 0.05, "val_loss": 0.07,
      "metrics": {"f1": 0.9}}),
    ("/api/mlops/system/log-resources", {"cpu_percent": 40.0, "memory_percent": 55.0}),
    ("/api/mlops/system/log-endpoint-health",
     {"endpoint": "/api/x", "status_code": 200, "response_time_ms": 33.0, "success": True}),
]


@pytest.mark.parametrize("path,payload", POST_CASES)
def test_mlops_post_endpoints(client, path, payload):
    r = client.post(path, json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "logged"
