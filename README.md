## 🔮 KubeOracle — AI Kubernetes Observability Dashboard

> Hackathon project for ABB Accelerator 2026 | Team of 4

---

## ⚡ FASTEST WAY TO RUN (5 minutes, no Docker needed)

### Step 1 — Start the Frontend

Open Terminal 1:

```bash
cd kubeoracle/frontend
npm install
npm run dev
```

✅ Dashboard opens at: **http://localhost:3000**

> The frontend has ALL mock data built-in. It works 100% without the backend.

---

### Step 2 — Start the Backend (Optional but recommended)

Open Terminal 2:

```bash
cd kubeoracle/backend

# Create virtual environment
python -m venv venv

# Activate it (Mac/Linux):
source venv/bin/activate
# Activate it (Windows):
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Optional: add your ANTHROPIC_API_KEY to .env for real AI

# Run backend
uvicorn main:app --reload --port 8000
```

✅ API running at: **http://localhost:8000**

---

## 🐳 Alternative: Run with Docker (one command)

```bash
cd kubeoracle
docker-compose up --build
```

Dashboard: http://localhost:3000

---

## ☸️ Optional: Real Minikube Setup (for extra judge points)

### Install Minikube
```bash
# Mac
brew install minikube

# Windows — download from: https://minikube.sigs.k8s.io/docs/start/
```

### Start Minikube
```bash
minikube start --cpus=4 --memory=4g
```

### Deploy fake services
```bash
kubectl apply -f kubeoracle/k8s/services.yaml
```

### Check pods are running
```bash
kubectl get pods -n kubeoracle
```

You'll see payment-service, auth-service, user-service, notification-service running.

---

## 🎬 HOW TO DEMO (Step by Step)

1. Open http://localhost:3000
2. Show the dashboard — explain the 4 services, metrics, AI insights
3. Click **"Simulate Failure"** on `payment-service`
4. Watch:
   - 🔴 Nodes turn red and pulse
   - ⚡ Blast radius spreads to auth-service + notification-service
   - 📊 Charts spike dramatically
   - 🚨 Alert feed fills with critical alerts
   - 🤖 AI panel updates with remediation insights
5. Show the AI-generated kubectl fix commands
6. Click "Reset Simulation" to restore

**Demo talking points:**
- "KubeOracle uses XGBoost ML to predict failures before they happen"
- "When a failure occurs, we visualize the cascade blast radius in real time"
- "Claude AI analyzes the failure and suggests exact kubectl remediation commands"
- "This can save engineering teams 30+ minutes of incident response time"

---

## 🎥 Recording the Demo Video

1. Use OBS Studio (free) or QuickTime (Mac)
2. Record at 1920x1080
3. Zoom into the dashboard so it fills the screen
4. Narrate while clicking through the simulation
5. Keep it 2-3 minutes max

---

## 📁 Project Structure

```
kubeoracle/
├── frontend/              # React + TypeScript dashboard
│   ├── src/
│   │   ├── components/    # All UI components
│   │   ├── pages/         # Dashboard page
│   │   ├── lib/           # Mock data + API client
│   │   └── types/         # TypeScript types
│   └── package.json
├── backend/               # FastAPI Python backend
│   ├── main.py            # Entry point
│   ├── mock_generator.py  # Synthetic metric generation
│   ├── ml/
│   │   └── predictor.py   # XGBoost failure prediction
│   └── routers/           # API endpoints
├── k8s/                   # Kubernetes YAML files
├── prometheus/            # Prometheus config
└── docker-compose.yml     # One-command startup
```

---
<!-- Contributor: samziya23  and Ishita-195 -->

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Framer Motion |
| Visualization | React Flow, Recharts |
| Backend | FastAPI (Python) |
| ML | XGBoost, scikit-learn |
| AI | Claude API (Anthropic) |
| DevOps | Docker, Minikube, Prometheus |

---

Built with ❤️ for ABB Accelerator 2026
