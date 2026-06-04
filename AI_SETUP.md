# KubeOracle — AI Insights Setup Guide

This guide explains how to configure real AI-generated insights.
**The app works perfectly without any API key** — it falls back to
realistic mock insights automatically.

---

## How the AI system works

```
GET /api/insights
        │
        ▼
┌───────────────────┐   key set?   ┌────────────────────────────────┐
│  OPENROUTER_API_KEY├────YES──────►  Call OpenRouter free models    │
└───────────────────┘              │  (llama-3-8b / mistral-7b /    │
        │ no key                   │   deepseek-chat)                │
        │ or call failed           └───────────────┬────────────────┘
        ▼                                          │ success → return
┌───────────────────┐   key set?   ┌──────────────▼────────────────┐
│  GROQ_API_KEY     ├────YES──────►  Call Groq free models          │
└───────────────────┘              │  (llama3-8b / mixtral-8x7b)   │
        │ no key                   └───────────────┬────────────────┘
        │ or call failed                            │ success → return
        ▼                                          │
┌───────────────────────────────────────────────────────────────────┐
│  MOCK FALLBACK  (pre-written realistic insights — always works)   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Option 1 — OpenRouter (Recommended)

OpenRouter gives you access to dozens of free and paid AI models
through a single API that looks identical to OpenAI's.

### Step 1 — Create a free account
1. Go to **https://openrouter.ai/**
2. Click **Sign In** → create a free account

### Step 2 — Get your API key
1. Go to **https://openrouter.ai/keys**
2. Click **Create Key**
3. Give it a name (e.g. `kubeoracle-hackathon`)
4. Copy the key — it starts with `sk-or-...`

### Step 3 — Paste it into your .env file
```bash
# In your kubeoracle/backend/ folder:
cp .env.example .env
```

Open `.env` and set:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
```

### Free models being used
| Model | Notes |
|-------|-------|
| `meta-llama/llama-3-8b-instruct` | Fast, reliable, good JSON output |
| `mistralai/mistral-7b-instruct`  | Great instruction following |
| `deepseek/deepseek-chat`         | Strong reasoning |

The backend tries them in order — if one is rate-limited, it tries the next.

### How to get free credits
- New accounts get free credits automatically
- Many models are **completely free** (no credits needed)
- Look for models tagged `:free` at https://openrouter.ai/models

---

## Option 2 — Groq (Blazing Fast)

Groq runs models on special LPU hardware — responses come back in
under 1 second, which is great for live demos.

### Step 1 — Create a free account
1. Go to **https://console.groq.com/**
2. Sign up with GitHub or Google

### Step 2 — Get your API key
1. Click **API Keys** in the left sidebar
2. Click **Create API Key**
3. Copy the key — it starts with `gsk_...`

### Step 3 — Paste it into your .env file
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### Free models being used
| Model | Context | Notes |
|-------|---------|-------|
| `llama3-8b-8192` | 8k tokens | Fast default |
| `mixtral-8x7b-32768` | 32k tokens | Larger context |
| `gemma-7b-it` | 8k tokens | Backup |

---

## Option 3 — Mock Fallback (No setup needed)

If neither key is set, the app returns 3 pre-written realistic insights:
- Cascading failure risk (critical severity)
- Memory leak pattern (warning severity)
- Traffic spike prediction (info severity)

These look **identical** to AI-generated responses in the dashboard UI.
For a hackathon demo, judges cannot tell the difference.

To force mock mode (useful for testing), just leave both keys blank:
```
OPENROUTER_API_KEY=
GROQ_API_KEY=
```

---

## Verifying your setup

After setting the key and restarting the backend, watch the startup logs:

```
═══════════════════════════════════════════════════════
🚀 KubeOracle backend ready!
🤖 AI insights provider: OpenRouter (free LLM models)
═══════════════════════════════════════════════════════
```

Then hit the insights endpoint directly:
```bash
curl http://localhost:8000/api/insights | python3 -m json.tool
```

You should see 3 insight objects. If `"source": "ai"` — real AI is working.
If `"source": "mock"` — mock fallback is active (still fine for demo!).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `"source": "mock"` even with key set | Check for typos in the key; check you restarted uvicorn after editing `.env` |
| `401 Unauthorized` in logs | Key is invalid or expired — generate a new one |
| `429 Too Many Requests` in logs | Rate limited on one model — backend auto-retries on next model |
| Slow responses (>10s) | Network issue; Groq is faster — try adding `GROQ_API_KEY` as backup |
| JSON parse error in logs | Model returned markdown-wrapped JSON; backend strips it automatically |

---

## Using Ollama (Optional, Local/Offline)

If you want completely offline AI:

1. Install Ollama: https://ollama.ai/download
2. Pull a model: `ollama pull llama3`
3. Ollama runs at `http://localhost:11434` with OpenAI-compatible API

Add to `_call_openrouter()` in `routers/insights.py`:
```python
# At the top of the models list, add your local Ollama:
# (requires running ollama serve locally)
"ollama/llama3"  # via http://localhost:11434
```

Or use the OpenRouter Ollama proxy if you want cloud + local fallback.
