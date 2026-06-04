#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# KubeOracle – Debugging Toolkit
# Usage: ./debug.sh <command> [args]
# ─────────────────────────────────────────────────────────────
set -euo pipefail

NS="${KUBEORACLE_NS:-kubeoracle}"
PROM_NS="kubeoracle-monitoring"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

header() { echo -e "\n${CYAN}══════ $* ══════${NC}"; }
info()   { echo -e "${GREEN}▶${NC} $*"; }

usage() {
  cat <<EOF
KubeOracle Debug Toolkit
Usage: $0 <command> [args]

Commands:
  pods            List all pods with status and restart counts
  logs <pod>      Tail logs from a pod (fuzzy match)
  events          Show recent cluster events (warnings first)
  top             Show CPU/memory for all pods
  describe <pod>  Full describe of a pod (fuzzy match)
  metrics <query> Run a PromQL query against Prometheus
  watch           Watch pods in real-time (refresh every 2s)
  health          Quick cluster health summary
  port-forward    Start all useful port-forwards
  crash-logs      Show logs from last crashed container
  network <pod>   Debug network from inside a pod

EOF
}

# ── pod listing ──────────────────────────────────────────────
cmd_pods() {
  header "Pods in namespace: $NS"
  kubectl get pods -n "$NS" \
    -o custom-columns="NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp,NODE:.spec.nodeName" \
    --sort-by='.status.containerStatuses[0].restartCount' 2>/dev/null \
    || kubectl get pods -n "$NS"

  header "Pods in demo namespace"
  kubectl get pods -n kubeoracle-demo 2>/dev/null || true
}

# ── log viewer ───────────────────────────────────────────────
cmd_logs() {
  local search="${1:-}"
  if [[ -z "$search" ]]; then
    echo "Usage: $0 logs <pod-name-or-prefix>"
    exit 1
  fi
  local pod
  pod=$(kubectl get pods -n "$NS" --no-headers | grep "$search" | head -1 | awk '{print $1}')
  if [[ -z "$pod" ]]; then
    echo "No pod matching '$search' found in $NS"
    exit 1
  fi
  info "Tailing logs for pod: $pod"
  kubectl logs -f "$pod" -n "$NS" --tail=100
}

# ── events ───────────────────────────────────────────────────
cmd_events() {
  header "Recent Warning Events"
  kubectl get events -n "$NS" --field-selector type=Warning \
    --sort-by='.lastTimestamp' 2>/dev/null | tail -30 || echo "No warnings"

  header "All Recent Events"
  kubectl get events -n "$NS" --sort-by='.lastTimestamp' | tail -20
}

# ── resource usage ───────────────────────────────────────────
cmd_top() {
  header "Pod Resource Usage"
  kubectl top pods -n "$NS" --sort-by=cpu 2>/dev/null || echo "metrics-server not available"
  echo ""
  header "Node Resource Usage"
  kubectl top nodes 2>/dev/null || echo "metrics-server not available"
}

# ── pod describe ─────────────────────────────────────────────
cmd_describe() {
  local search="${1:-}"
  if [[ -z "$search" ]]; then
    echo "Usage: $0 describe <pod-name-or-prefix>"
    exit 1
  fi
  local pod
  pod=$(kubectl get pods -n "$NS" --no-headers | grep "$search" | head -1 | awk '{print $1}')
  if [[ -z "$pod" ]]; then
    echo "No pod matching '$search' found"
    exit 1
  fi
  kubectl describe pod "$pod" -n "$NS"
}

# ── promql query ─────────────────────────────────────────────
cmd_metrics() {
  local query="${1:-up}"
  info "Forwarding Prometheus port..."
  kubectl port-forward svc/prometheus 9091:9090 -n "$PROM_NS" &>/dev/null &
  PF_PID=$!
  sleep 2
  info "Running PromQL: $query"
  curl -s "http://localhost:9091/api/v1/query?query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(r['metric'], '->', r['value'][1]) for r in d['data']['result']]"
  kill $PF_PID 2>/dev/null || true
}

# ── watch ────────────────────────────────────────────────────
cmd_watch() {
  info "Watching pods in $NS (Ctrl+C to stop)"
  watch -n 2 "kubectl get pods -n $NS -o wide"
}

# ── health summary ───────────────────────────────────────────
cmd_health() {
  header "Cluster Health Summary"

  echo -e "\n${YELLOW}Nodes:${NC}"
  kubectl get nodes -o custom-columns="NAME:.metadata.name,STATUS:.status.conditions[-1].type,READY:.status.conditions[-1].status,VERSION:.status.nodeInfo.kubeletVersion"

  echo -e "\n${YELLOW}Deployments:${NC}"
  kubectl get deployments -n "$NS" -o custom-columns="NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas"

  echo -e "\n${YELLOW}Services:${NC}"
  kubectl get services -n "$NS"

  echo -e "\n${YELLOW}StatefulSets:${NC}"
  kubectl get statefulsets -n "$NS" 2>/dev/null || echo "none"

  echo -e "\n${YELLOW}Pods with restarts > 0:${NC}"
  kubectl get pods -n "$NS" --no-headers | awk '$5 > 0' || echo "none"

  echo -e "\n${YELLOW}Prometheus:${NC}"
  kubectl get pods -n "$PROM_NS" 2>/dev/null || echo "not deployed"
}

# ── port-forward all ─────────────────────────────────────────
cmd_port_forward() {
  info "Starting port-forwards (background)..."
  kubectl port-forward svc/kubeoracle-backend  8000:8000 -n "$NS"             &
  kubectl port-forward svc/kubeoracle-frontend 3000:80   -n "$NS"             &
  kubectl port-forward svc/prometheus          9090:9090 -n "$PROM_NS"        &
  echo ""
  info "Port-forwards started:"
  echo "  Backend:    http://localhost:8000"
  echo "  Frontend:   http://localhost:3000"
  echo "  Prometheus: http://localhost:9090"
  echo ""
  echo "Kill all: pkill -f 'kubectl port-forward'"
  wait
}

# ── crash logs ───────────────────────────────────────────────
cmd_crash_logs() {
  header "Crash Logs (previous containers)"
  local pods
  pods=$(kubectl get pods -n "$NS" --no-headers | awk '{print $1}')
  for pod in $pods; do
    local restarts
    restarts=$(kubectl get pod "$pod" -n "$NS" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo 0)
    if [[ "$restarts" -gt 0 ]]; then
      info "Pod $pod had $restarts restarts. Previous container logs:"
      kubectl logs "$pod" -n "$NS" --previous --tail=50 2>/dev/null || echo "  (no previous logs available)"
      echo ""
    fi
  done
}

# ── network debug ────────────────────────────────────────────
cmd_network() {
  local pod="${1:-}"
  if [[ -z "$pod" ]]; then
    pod=$(kubectl get pods -n "$NS" --no-headers | head -1 | awk '{print $1}')
  fi
  info "Network debug from pod: $pod"
  kubectl exec "$pod" -n "$NS" -- sh -c "
    echo '=== /etc/resolv.conf ==='
    cat /etc/resolv.conf
    echo '=== DNS test ==='
    nslookup kubernetes.default.svc.cluster.local 2>&1 | head -5
    echo '=== Services reachable ==='
    for svc in kubeoracle-backend redis postgres; do
      echo -n \"  \$svc: \"
      wget -qO- --timeout=2 http://\$svc:8000/health 2>&1 | head -1 || echo 'unreachable'
    done
  " 2>/dev/null || echo "exec not available on this pod"
}

# ── dispatch ─────────────────────────────────────────────────
case "${1:-help}" in
  pods)          cmd_pods ;;
  logs)          cmd_logs "${2:-}" ;;
  events)        cmd_events ;;
  top)           cmd_top ;;
  describe)      cmd_describe "${2:-}" ;;
  metrics)       cmd_metrics "${2:-up}" ;;
  watch)         cmd_watch ;;
  health)        cmd_health ;;
  port-forward)  cmd_port_forward ;;
  crash-logs)    cmd_crash_logs ;;
  network)       cmd_network "${2:-}" ;;
  *)             usage ;;
esac
