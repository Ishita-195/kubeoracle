# 🔮 KubeOracle

> **Predictive Kubernetes observability & self-healing** — powered by XGBoost, FastAPI, React, and Prometheus.

Built for **ABB Accelerator 2026**. KubeOracle visualizes Kubernetes cluster
health in real time, predicts service failures, simulates blast radius, and
generates AI-assisted `kubectl` remediation commands.

![Status](https://img.shields.io/badge/status-hackathon-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-61DAFB)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)

---

## ✨ Features

- **Live topology view** — services, dependencies, and health rendered with React Flow.
- **Failure simulation** — inject a fault and watch the blast radius propagate.
- **Predictive ML** — XGBoost model flags services likely to fail.
- **AI remediation** — generates suggested `kubectl` fix commands.
- **Metrics & alerts** — Prometheus-backed metrics with a live alert feed.
- **Works offline** — the frontend ships with built-in mock data and runs fully without the backend.

---

## ⚡ Quick Start (5 minutes, no Docker required)

### 1. Frontend

```bash
cd frontend
npm install
npm run dev

Dashboard → http://localhost:3000

The frontend includes built-in mock data and works 100% without the backend.

2. Backend (optional, recommended)
cd backend
python -m venv venv

# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # then add your API key (see AI Setup)
uvicorn main:app --reload --port 8000
API → http://localhost:8000 · Docs → http://localhost:8000/docs

🐳 Run with Docker
From the repository root:

docker-compose up --build
☸️ Optional: Real Minikube Setup
Deploy against a real cluster using the manifests in k8s/:

minikube start
kubectl apply -f k8s/
kubectl get pods
🤖 AI Setup
KubeOracle auto-detects an AI provider at startup based on the API key present
in your .env:

Provider	Env var
OpenRouter	OPENROUTER_API_KEY
Groq	GROQ_API_KEY
Mock fallback	(none required)
If no key is set, the backend runs in mock mode so the demo still works.
See AI_SETUP.md for full details.

🎬 Demo Script
Open http://localhost:3000.
Review the dashboard — 4 services with live metrics.
Click Simulate Failure on payment-service.
Watch the red nodes, blast-radius graph, and alert feed update.
Review the AI-generated kubectl remediation commands.
Click Reset Simulation to restore healthy state.
📁 Project Structure
.
├── frontend/             # React + TypeScript dashboard
├── backend/              # FastAPI service (services, simulations, insights, mlops routers)
├── mlops/                # ML training & model artifacts
├── kubeoracle-devops/    # DevOps / deployment tooling
├── k8s/                  # Kubernetes manifests
├── prometheus/           # Prometheus configuration
├── .github/workflows/    # CI pipelines
├── AI_SETUP.md           # AI provider configuration guide
└── docker-compose.yml
🛠 Tech Stack
Layer	Technologies
Frontend	React, TypeScript, Tailwind CSS, Framer Motion
Visualization	React Flow, Recharts
Backend	FastAPI (Python)
ML	XGBoost, scikit-learn
AI	OpenRouter / Groq (with mock fallback)
DevOps	Docker, Minikube, Prometheus
