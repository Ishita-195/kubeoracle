#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# KubeOracle – Docker Build & Push Script
# Usage: ./build-images.sh [--push] [--registry REGISTRY] [--tag TAG]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

PUSH=false
REGISTRY="${DOCKER_REGISTRY:-}"
TAG="${IMAGE_TAG:-latest}"
USE_MINIKUBE_REGISTRY=false

for arg in "$@"; do
  case $arg in
    --push)              PUSH=true ;;
    --minikube)          USE_MINIKUBE_REGISTRY=true ;;
    --registry=*)        REGISTRY="${arg#*=}" ;;
    --tag=*)             TAG="${arg#*=}" ;;
  esac
done

# ── Use Minikube's internal Docker daemon ────────────────────
if $USE_MINIKUBE_REGISTRY; then
  info "Using Minikube Docker daemon"
  eval "$(minikube -p kubeoracle docker-env)"
fi

# ── Build backend ────────────────────────────────────────────
BACKEND_IMAGE="${REGISTRY:+$REGISTRY/}kubeoracle-backend:$TAG"
info "Building backend: $BACKEND_IMAGE"
docker build \
  -f backend.Dockerfile \
  -t "$BACKEND_IMAGE" \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
  .

# ── Build frontend ───────────────────────────────────────────
FRONTEND_IMAGE="${REGISTRY:+$REGISTRY/}kubeoracle-frontend:$TAG"
info "Building frontend: $FRONTEND_IMAGE"
docker build \
  -f frontend.Dockerfile \
  -t "$FRONTEND_IMAGE" \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  .

# ── Push images ──────────────────────────────────────────────
if $PUSH; then
  if [[ -z "$REGISTRY" ]]; then
    warn "No --registry specified, pushing to Docker Hub (requires docker login)"
  fi
  info "Pushing $BACKEND_IMAGE"
  docker push "$BACKEND_IMAGE"
  info "Pushing $FRONTEND_IMAGE"
  docker push "$FRONTEND_IMAGE"
fi

echo ""
info "Build complete!"
echo "  Backend:  $BACKEND_IMAGE"
echo "  Frontend: $FRONTEND_IMAGE"
echo ""
if ! $PUSH; then
  echo "  To push: ./build-images.sh --push --registry=YOUR_DOCKERHUB_USER --tag=$TAG"
fi
if $USE_MINIKUBE_REGISTRY; then
  echo ""
  echo "  Images loaded into Minikube. Update your manifests to use:"
  echo "    image: kubeoracle-backend:$TAG"
  echo "    imagePullPolicy: Never"
fi
