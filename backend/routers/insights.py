"""
routers/insights.py — AI-powered insights via OpenRouter (primary) / Groq (secondary) / Mock (fallback)

Priority order:
  1. OpenRouter  → set OPENROUTER_API_KEY in .env
  2. Groq        → set GROQ_API_KEY in .env
  3. Mock        → always works, no API key needed

The app NEVER crashes — if both keys are missing or calls fail,
it silently falls back to realistic pre-written insights.
"""

import os
import json
import httpx
from fastapi import APIRouter
from mock_generator import get_all_metrics

router = APIRouter(prefix="/api", tags=["insights"])

# ─────────────────────────────────────────────────────────────────────────────
# Fallback mock insights (used when no API key is set, or any call fails)
# ─────────────────────────────────────────────────────────────────────────────
FALLBACK_INSIGHTS = [
    {
        "id": "i1",
        "title": "Cascading Failure Risk Detected",
        "description": (
            "auth-service is at 67% failure probability. "
            "If it fails, payment-service loses authentication within 30–60 seconds."
        ),
        "action": "kubectl scale deployment/auth-service --replicas=4",
        "severity": "critical",
        "confidence": 91,
        "source": "mock",
    },
    {
        "id": "i2",
        "title": "Memory Leak Pattern in auth-service",
        "description": (
            "Memory grew 22% over 2 hours with no traffic spike. "
            "OOMKill likely within ~2 hours."
        ),
        "action": "kubectl rollout restart deployment/auth-service",
        "severity": "warning",
        "confidence": 84,
        "source": "mock",
    },
    {
        "id": "i3",
        "title": "Traffic Spike Anticipated",
        "description": (
            "Historical patterns predict 3x traffic on notification-service in 45 min. "
            "Current 2 replicas will be insufficient."
        ),
        "action": "kubectl scale deployment/notification-service --replicas=4",
        "severity": "info",
        "confidence": 76,
        "source": "mock",
    },
]

SYSTEM_PROMPT = (
    "You are KubeOracle's AI engine specialising in Kubernetes reliability. "
    "Analyse the provided cluster metrics and return ONLY a valid JSON array — "
    "no markdown, no backticks, no explanation. Raw JSON only. "
    "The array must contain exactly 3 objects each with keys: "
    "id (string), title (string, max 8 words), description (string, 1-2 sentences), "
    "action (string — a concrete kubectl command or fix), "
    "severity ('info'|'warning'|'critical'), confidence (integer 0-100), source ('ai')."
)


def _metrics_text() -> str:
    metrics = get_all_metrics()
    return "\n".join(
        f"- {m['service']}: CPU={m['cpu']:.1f}%, MEM={m['memory']:.1f}%, "
        f"restarts={m['restarts']}, latency={m['latency']:.0f}ms, "
        f"errorRate={m['error_rate']:.1f}%, status={m['status']}"
        for m in metrics
    )


def _parse_ai_response(text: str) -> list | None:
    """Strip markdown fences and parse JSON."""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. OpenRouter  (free models: llama-3-8b, mistral-7b, deepseek-chat)
# ─────────────────────────────────────────────────────────────────────────────
def _call_openrouter(prompt: str) -> list | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    models = [
        "meta-llama/llama-3-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "deepseek/deepseek-chat",
        "microsoft/phi-3-mini-128k-instruct:free",
    ]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kubeoracle.hackathon",
        "X-Title": "KubeOracle",
    }

    for model in models:
        try:
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 900,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Cluster metrics:\n{prompt}\n\nGenerate 3 insights."},
                    ],
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            result = _parse_ai_response(text)
            if result:
                print(f"✅ OpenRouter ({model}) OK")
                return result
        except Exception as e:
            print(f"⚠️  OpenRouter {model}: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Groq  (extremely fast free tier — llama3, mixtral, gemma)
# ─────────────────────────────────────────────────────────────────────────────
def _call_groq(prompt: str) -> list | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    models = ["llama3-8b-8192", "mixtral-8x7b-32768", "gemma-7b-it"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for model in models:
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 900,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Cluster metrics:\n{prompt}\n\nGenerate 3 insights."},
                    ],
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            result = _parse_ai_response(text)
            if result:
                print(f"✅ Groq ({model}) OK")
                return result
        except Exception as e:
            print(f"⚠️  Groq {model}: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/insights")
def get_insights():
    """
    Returns 3 AI-generated Kubernetes insights.
    Priority: OpenRouter → Groq → Mock (never crashes).
    """
    prompt = _metrics_text()

    result = _call_openrouter(prompt)
    if result:
        return result

    result = _call_groq(prompt)
    if result:
        return result

    print("ℹ️  No API key / all calls failed — serving mock insights.")
    return FALLBACK_INSIGHTS


@router.get("/alerts")
def get_alerts():
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    return [
        {
            "id": "a1",
            "service": "auth-service",
            "severity": "warning",
            "message": "CPU at 72% — ML model predicts 67% failure probability.",
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "acknowledged": False,
        },
        {
            "id": "a2",
            "service": "auth-service",
            "severity": "warning",
            "message": "Elevated restart count (2 in last 1h). OOMKill suspected.",
            "timestamp": (now - timedelta(minutes=4)).isoformat(),
            "acknowledged": False,
        },
        {
            "id": "a3",
            "service": "payment-service",
            "severity": "info",
            "message": "Latency P99 at 120ms. Within acceptable range.",
            "timestamp": (now - timedelta(minutes=6)).isoformat(),
            "acknowledged": True,
        },
    ]
