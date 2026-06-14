# KubeOracle

> **AI-powered Kubernetes failure prediction & self-healing platform** — built with XGBoost, FastAPI, React, and Prometheus.

[![Status](https://img.shields.io/badge/status-hackathon-blue)](https://github.com/Ishita-195/kubeoracle)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-61DAFB)](https://github.com/Ishita-195/kubeoracle)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://github.com/Ishita-195/kubeoracle)
[![ML](https://img.shields.io/badge/ML-XGBoost%2094%25%20F1-orange)](https://github.com/Ishita-195/kubeoracle)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

KubeOracle is a **predictive observability platform** that monitors live Kubernetes cluster health, forecasts service failures before they happen, simulates blast radius impact, and surfaces AI-generated `kubectl` remediation commands — all from a single real-time dashboard.

Built for **ABB Accelerator 2026**.

---

## What It Does

| Capability | Description |
|---|---|
| **Failure Prediction** | XGBoost model (94% F1-score) flags services likely to fail based on live metrics |
| **Blast Radius Simulation** | Inject a fault and visualize cascading failure propagation across the service graph |
| **AI Remediation** | Auto-generates context-aware `kubectl` fix commands using OpenRouter / Groq |
| **Live Topology View** | React Flow graph of services, dependencies, and real-time health status |
| **MLOps Drift Detection** | PSI-based data drift monitoring with live dashboards and retraining triggers |
| **Metrics & Alerts** | Prometheus-backed metrics with a live alert feed |
| **Offline-Ready** | Frontend ships with built-in mock data — works 100% without a backend |

---

## Quick Start

### Frontend (2 minutes, no backend needed)

```bash
cd frontend
npm install
npm run dev
```

Dashboard → [http://localhost:3000](http://localhost:3000)

> The frontend runs fully with built-in mock data. No backend or cluster required.

### Backend (optional, recommended)

```bash
cd backend
python -m venv venv

# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # Add your AI provider key (see AI Setup below)
uvicorn main:app --reload --port 8000
```

API → `http://localhost:8000` · Swagger Docs → `http://localhost:8000/docs`

### Docker (one command)

```bash
docker-compose up --build
```

### Kubernetes (Minikube)

```bash
minikube start
kubectl apply -f k8s/
kubectl get pods
```

---

## AI Setup

KubeOracle auto-detects your AI provider at startup based on the key present in `.env`:

| Provider | Environment Variable |
|---|---|
| OpenRouter | `OPENROUTER_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Mock fallback | *(no key required)* |

No key? The backend runs in mock mode — the full demo still works.  
See [`AI_SETUP.md`](AI_SETUP.md) for detailed configuration.

---

## Live Demo Walkthrough

1. Open [http://localhost:3000](http://localhost:3000)
2. Review the dashboard — 4 services with live health metrics
3. Click **Simulate Failure** on `payment-service`
4. Watch red nodes, blast-radius propagation, and the alert feed update in real time
5. Review AI-generated `kubectl` remediation commands in the insights panel
6. Click **Reset Simulation** to restore healthy state

---

## Project Structure

```
kubeoracle/
├── frontend/                  # React + TypeScript dashboard
│   └── src/
│       ├── components/        # Topology, alerts, MLOps dashboards
│       └── mock/              # Built-in offline mock data
├── backend/                   # FastAPI service
│   └── routers/               # services, simulations, insights, mlops
├── mlops/                     # XGBoost training pipeline & model artifacts
├── k8s/                       # Kubernetes manifests (3 namespaces)
├── prometheus/                # Prometheus scrape config
├── kubeoracle-devops/         # Helm chart, CI/CD tooling
├── .github/
│   └── workflows/             # GitHub Actions CI pipelines
├── docker-compose.yml
└── AI_SETUP.md
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React, TypeScript, Tailwind CSS, Framer Motion |
| **Visualization** | React Flow, Recharts |
| **Backend** | FastAPI (Python) |
| **Machine Learning** | XGBoost (94% F1), scikit-learn, PSI-based drift detection |
| **AI / LLM** | OpenRouter, Groq (with mock fallback) |
| **DevOps** | Docker, Minikube, Kubernetes, Prometheus, GitHub Actions, Helm |

---

## Model Performance

| Metric | Score |
|---|---|
| F1-Score | **94%** |
| Drift Detection | PSI + KL Divergence |
| Retraining Trigger | Automated on drift threshold breach |

## Authors & Contributors

**Ishita Anand** 
[GitHub](https://github.com/Ishita-195)

**Samridhi Shashwat**
[GitHub](https://github.com/samziya23)

**Ramanuj Sahu**
[GitHub](https://github.com/RamanujSahu432)

---

*Built with ❤️ for ABB Accelerator 2026*
