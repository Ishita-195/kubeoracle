#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# KubeOracle – Local Cluster Setup
# Sets up Minikube with proper resources, addons, namespaces
# Usage: ./setup-cluster.sh [--reset]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

PROFILE="kubeoracle"
CPUS=4
MEMORY="8192"  # MB
DISK="40g"
K8S_VERSION="v1.29.0"

# ── Parse flags ─────────────────────────────────────────────
RESET=false
for arg in "$@"; do
  [[ "$arg" == "--reset" ]] && RESET=true
done

# ── Prerequisite check ───────────────────────────────────────
for cmd in minikube kubectl docker helm; do
  command -v "$cmd" &>/dev/null || error "$cmd is not installed. Please install it first."
done

# ── Optionally reset ─────────────────────────────────────────
if $RESET; then
  warn "Deleting existing Minikube profile: $PROFILE"
  minikube delete -p "$PROFILE" || true
fi

# ── Start Minikube ───────────────────────────────────────────
info "Starting Minikube (profile=$PROFILE, cpus=$CPUS, memory=${MEMORY}MB)"
if minikube status -p "$PROFILE" &>/dev/null; then
  info "Minikube already running, skipping start"
else
  minikube start \
    --profile="$PROFILE" \
    --cpus="$CPUS" \
    --memory="$MEMORY" \
    --disk-size="$DISK" \
    --kubernetes-version="$K8S_VERSION" \
    --driver=docker \
    --addons=metrics-server,ingress,dashboard \
    --extra-config=kubelet.max-pods=200
fi

# Set kubectl context
kubectl config use-context "$PROFILE"
info "kubectl context set to: $PROFILE"

# ── Enable required addons ───────────────────────────────────
info "Enabling Minikube addons"
minikube addons enable metrics-server   -p "$PROFILE" || true
minikube addons enable ingress          -p "$PROFILE" || true
minikube addons enable dashboard        -p "$PROFILE" || true
minikube addons enable registry         -p "$PROFILE" || true

# ── Create namespaces ────────────────────────────────────────
info "Creating namespaces"
kubectl apply -f k8s/namespaces/namespaces.yaml

# ── Wait for metrics-server ──────────────────────────────────
info "Waiting for metrics-server to be ready..."
kubectl rollout status deployment/metrics-server -n kube-system --timeout=120s || warn "metrics-server not ready yet"

# ── Deploy ConfigMaps & Secrets ──────────────────────────────
info "Applying ConfigMaps and Secrets"
kubectl apply -f k8s/configmaps/

# ── Deploy Prometheus stack ──────────────────────────────────
info "Deploying Prometheus"
kubectl apply -f k8s/prometheus/prometheus-deployment.yaml
kubectl rollout status deployment/prometheus -n kubeoracle-monitoring --timeout=120s || warn "Prometheus still starting..."

# ── Deploy backend & frontend ────────────────────────────────
info "Deploying KubeOracle application"
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/

# ── Deploy demo services ─────────────────────────────────────
info "Deploying demo microservices"
kubectl apply -f k8s/demo-services/

# ── Wait for rollouts ────────────────────────────────────────
info "Waiting for deployments to be ready..."
for deploy in kubeoracle-backend kubeoracle-frontend redis; do
  kubectl rollout status deployment/$deploy -n kubeoracle --timeout=120s || warn "$deploy not ready yet"
done

# ── Print access URLs ────────────────────────────────────────
MINIKUBE_IP=$(minikube ip -p "$PROFILE")
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  KubeOracle cluster is READY!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "  Frontend:    http://${MINIKUBE_IP}:30080"
echo "  Backend API: http://${MINIKUBE_IP}:30080/api  (via frontend NodePort)"
echo "  Prometheus:  http://${MINIKUBE_IP}:30090"
echo "  API Gateway: http://${MINIKUBE_IP}:30081"
echo ""
echo "  Dashboard: minikube dashboard -p $PROFILE"
echo ""
echo "  Port-forward backend locally:"
echo "    kubectl port-forward svc/kubeoracle-backend 8000:8000 -n kubeoracle"
echo ""
