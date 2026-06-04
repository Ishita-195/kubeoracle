# KubeOracle – DevOps & Deployment Guide

> **Member 4: DevOps + Deployment Engineering**
> Complete infrastructure for local Kubernetes, Prometheus, Docker, CI/CD, and demo workloads.

---

## 📁 Directory Structure

```
devops/
├── backend.Dockerfile          # Multi-stage FastAPI build
├── frontend.Dockerfile         # Multi-stage React + Nginx build
├── k8s/
│   ├── namespaces/             # kubeoracle, kubeoracle-monitoring, kubeoracle-demo
│   ├── configmaps/             # ConfigMaps + Secrets
│   ├── backend/                # FastAPI Deployment (3 replicas) + HPA + RBAC
│   ├── frontend/               # React Deployment (2 replicas) NodePort
│   ├── postgres/               # PostgreSQL StatefulSet + headless service
│   ├── redis/                  # Redis Deployment + sidecar exporter
│   ├── demo-services/          # 8 microservices for dependency graph demo
│   └── prometheus/             # Prometheus Deployment + RBAC + alert rules
├── workload-generator/
│   ├── workload_generator.py   # Synthetic load script (CPU, crash, memory, cascade)
│   └── workload-generator-k8s.yaml  # K8s Deployment for the generator
├── helm/
│   └── kubeoracle/             # Helm chart (one-command deploy)
│       ├── Chart.yaml
│       └── values.yaml
├── scripts/
│   ├── setup-cluster.sh        # Minikube setup (4 CPU, 8GB RAM)
│   ├── build-images.sh         # Docker build + push helper
│   └── debug.sh                # Debugging toolkit
└── .github/
    └── workflows/
        └── ci-cd.yml           # GitHub Actions CI/CD pipeline
```

---

## 🚀 Quick Start (Local Demo)

### 1. Prerequisites

```bash
# Install required tools
brew install minikube kubectl helm docker  # macOS
# or follow official docs for Linux/Windows
```

### 2. Start the Cluster

```bash
cd devops/
chmod +x scripts/*.sh
./scripts/setup-cluster.sh
```

This automatically:
- Starts Minikube with **4 CPU / 8GB RAM**
- Enables `metrics-server`, `ingress`, `dashboard`
- Creates all namespaces
- Deploys Prometheus, backend, frontend, demo services

### 3. Build & Load Docker Images

```bash
# Option A: Load into Minikube directly (no registry needed)
./scripts/build-images.sh --minikube --tag latest

# Option B: Push to Docker Hub
./scripts/build-images.sh --push --registry=YOUR_DOCKERHUB_USER --tag latest
```

> **Important:** After building, update the `image:` field in `k8s/backend/backend-deployment.yaml` and `k8s/frontend/frontend-deployment.yaml` with your registry/tag.

### 4. Apply Kubernetes Manifests

```bash
# Apply everything in order
kubectl apply -f k8s/namespaces/
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/
kubectl apply -f k8s/demo-services/
kubectl apply -f k8s/prometheus/

# Verify all pods are running
kubectl get pods -n kubeoracle
```

### 5. Access the Services

| Service    | Access method                                         |
|------------|-------------------------------------------------------|
| Frontend   | `minikube ip` → port 30080, e.g. `http://192.168.x.x:30080` |
| Backend    | `kubectl port-forward svc/kubeoracle-backend 8000:8000 -n kubeoracle` |
| Prometheus | `http://$(minikube ip):30090`                        |
| Dashboard  | `minikube dashboard -p kubeoracle`                   |

---

## 🔥 Workload Generator (Demo Scenarios)

The workload generator creates realistic cluster events for a compelling demo.

### Run locally (against your cluster):

```bash
cd workload-generator/
pip install asyncio
python workload_generator.py --scenario random --duration 600
```

### Available scenarios:

| Scenario   | What it does                                            |
|------------|---------------------------------------------------------|
| `cpu_spike`  | Busy-loop inside a pod → CPU alert triggers          |
| `memory_leak`| Fills memory → potential OOMKill                    |
| `crash_loop` | Deletes pods repeatedly → CrashLoopBackOff          |
| `cascading`  | auth → payment cascade failure + recovery            |
| `transient`  | Scale-to-zero then restore → brief outage            |
| `quiet`      | Let everything settle                                 |
| `random`     | Cycles through all scenarios (best for demos)        |

### Deploy as a pod (runs continuously):

```bash
kubectl apply -f workload-generator/workload-generator-k8s.yaml
```

---

## 📊 Prometheus

### Access Prometheus

```bash
# Via NodePort (Minikube)
open http://$(minikube ip -p kubeoracle):30090

# Or port-forward
kubectl port-forward svc/prometheus 9090:9090 -n kubeoracle-monitoring
open http://localhost:9090
```

### Key PromQL queries for the demo:

```promql
# Pod CPU usage by pod
rate(container_cpu_usage_seconds_total{namespace="kubeoracle"}[2m])

# Pod memory usage
container_memory_working_set_bytes{namespace="kubeoracle"}

# Pod restart count
kube_pod_container_status_restarts_total{namespace="kubeoracle"}

# Pods not ready
kube_pod_status_ready{condition="false", namespace="kubeoracle"}

# Deployment replica mismatch
kube_deployment_spec_replicas{namespace="kubeoracle"}
  != kube_deployment_status_available_replicas{namespace="kubeoracle"}
```

---

## 🛠 Debugging Toolkit

```bash
./scripts/debug.sh <command>

# Commands:
./scripts/debug.sh health          # Full cluster health summary
./scripts/debug.sh pods            # All pods with restart counts
./scripts/debug.sh logs backend    # Tail backend logs (fuzzy match)
./scripts/debug.sh events          # Warning events first
./scripts/debug.sh top             # CPU/memory usage
./scripts/debug.sh crash-logs      # Previous container logs for crashed pods
./scripts/debug.sh describe auth   # Full describe (fuzzy pod name)
./scripts/debug.sh metrics 'up'    # Run PromQL query
./scripts/debug.sh watch           # Real-time pod watch
./scripts/debug.sh port-forward    # Start all port-forwards
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

### Required GitHub Secrets

| Secret              | Value                                         |
|---------------------|-----------------------------------------------|
| `DOCKERHUB_USERNAME`| Your Docker Hub username                      |
| `DOCKERHUB_TOKEN`   | Docker Hub access token (Settings → Security) |
| `KUBECONFIG_BASE64` | `base64 ~/.kube/config` (for auto-deploy)     |

### Pipeline flow

```
push to main
  └── test (pytest + npm build)
       └── build (docker build + push with SHA tag)
            └── deploy (kubectl set image + rollout status)
```

---

## ⛵ Helm Chart (One-Command Deploy)

```bash
# Install KubeOracle with Helm
helm install kubeoracle ./helm/kubeoracle \
  --set backend.secrets.anthropicApiKey=YOUR_KEY \
  --set postgres.auth.password=YOUR_PG_PASS \
  --set redis.auth.password=YOUR_REDIS_PASS \
  --set global.imageRegistry=YOUR_DOCKERHUB_USER

# Upgrade
helm upgrade kubeoracle ./helm/kubeoracle --reuse-values

# Uninstall
helm uninstall kubeoracle
```

---

## 🧩 Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │         kubeoracle namespace      │
                    │                                   │
  User ──► NodePort │  Frontend (2x) ──► Backend (3x)  │
  :30080            │                     │             │
                    │              ┌──────┴──────┐      │
                    │           Postgres       Redis    │
                    │           StatefulSet    Cache    │
                    │                                   │
                    │  Demo Microservices (8 services)  │
                    │  payment, auth, user, order...    │
                    └─────────────────────────────────┘
                    
                    ┌─────────────────────────────────┐
                    │    kubeoracle-monitoring ns       │
                    │                                   │
  :30090 ──► NodePort│  Prometheus ← kube-state-metrics│
                    │     (72h retention, alerts)       │
                    └─────────────────────────────────┘
```

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| Pods in `Pending` | Check `kubectl describe pod <name>` for resource limits. Increase Minikube memory. |
| `ImagePullBackOff` | Run `./scripts/build-images.sh --minikube` to load images locally, then set `imagePullPolicy: Never` |
| `CrashLoopBackOff` | Run `./scripts/debug.sh crash-logs` to see previous container output |
| Prometheus unreachable | `kubectl get pods -n kubeoracle-monitoring` — check RBAC with `kubectl auth can-i list pods --as=system:serviceaccount:kubeoracle-monitoring:prometheus-sa` |
| `metrics-server` not working | `minikube addons enable metrics-server -p kubeoracle` |
| Backend can't reach Prometheus | Check `PROMETHEUS_URL` in ConfigMap matches `http://prometheus.kubeoracle-monitoring.svc.cluster.local:9090` |
