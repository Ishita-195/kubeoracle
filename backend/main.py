"""
main.py — KubeOracle FastAPI Backend
Run with: uvicorn main:app --reload --port 8000
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers.services import router as services_router  # noqa: E402
from routers.simulation import router as simulation_router  # noqa: E402
from routers.insights import router as insights_router  # noqa: E402
from routers.mlops import router as mlops_router  # noqa: E402

app = FastAPI(
    title="KubeOracle API",
    description="AI-powered Kubernetes observability backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(services_router)
app.include_router(simulation_router)
app.include_router(insights_router)
app.include_router(mlops_router)


@app.get("/")
def root():
    return {"status": "KubeOracle backend running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup_event():
    # Pre-train ML model
    from ml.predictor import get_model
    get_model()

    # Show which AI provider will be used
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    has_groq       = bool(os.getenv("GROQ_API_KEY", "").strip())

    if has_openrouter:
        provider = "OpenRouter (free LLM models)"
    elif has_groq:
        provider = "Groq (free LPU-accelerated models)"
    else:
        provider = "Mock insights (no API key set — still looks great!)"

    print("=" * 55)
    print("🚀 KubeOracle backend ready!")
    print(f"🤖 AI insights provider: {provider}")
    print("=" * 55)
