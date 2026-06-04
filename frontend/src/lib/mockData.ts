import type { ServiceMetrics, MetricHistory, Alert, ClusterHealth, AIInsight } from '../types'

export const SERVICES: ServiceMetrics[] = [
  {
    id: 'payment-service',
    name: 'payment-service',
    status: 'healthy',
    cpu: 34,
    memory: 52,
    restarts: 0,
    latency: 120,
    errorRate: 0.2,
    failureProbability: 12,
    replicas: 3,
    requestsPerSec: 847,
    uptime: '14d 6h',
    dependencies: ['auth-service', 'notification-service'],
  },
  {
    id: 'auth-service',
    name: 'auth-service',
    status: 'warning',
    cpu: 72,
    memory: 68,
    restarts: 2,
    latency: 340,
    errorRate: 1.8,
    failureProbability: 67,
    replicas: 2,
    requestsPerSec: 1203,
    uptime: '14d 6h',
    dependencies: ['user-service'],
  },
  {
    id: 'user-service',
    name: 'user-service',
    status: 'healthy',
    cpu: 28,
    memory: 41,
    restarts: 0,
    latency: 89,
    errorRate: 0.1,
    failureProbability: 8,
    replicas: 3,
    requestsPerSec: 562,
    uptime: '14d 6h',
    dependencies: [],
  },
  {
    id: 'notification-service',
    name: 'notification-service',
    status: 'healthy',
    cpu: 18,
    memory: 35,
    restarts: 0,
    latency: 67,
    errorRate: 0.05,
    failureProbability: 5,
    replicas: 2,
    requestsPerSec: 234,
    uptime: '14d 6h',
    dependencies: ['user-service'],
  },
]

export function generateMetricHistory(baseValue: number, length = 20, variance = 10): MetricHistory[] {
  const now = Date.now()
  return Array.from({ length }, (_, i) => {
    const t = new Date(now - (length - i) * 15000)
    const jitter = (Math.random() - 0.5) * variance
    return {
      time: t.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      cpu: Math.min(100, Math.max(0, baseValue + jitter)),
      memory: Math.min(100, Math.max(0, baseValue * 0.9 + jitter * 0.7)),
      latency: Math.max(10, 100 + jitter * 15),
      errorRate: Math.max(0, 0.5 + jitter * 0.05),
    }
  })
}

export function generateSpikedHistory(baseValue: number, length = 20): MetricHistory[] {
  const history = generateMetricHistory(baseValue, length - 5)
  const now = Date.now()
  const spikes = Array.from({ length: 5 }, (_, i) => {
    const t = new Date(now - (4 - i) * 15000)
    const spike = baseValue + 30 + i * 12
    return {
      time: t.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      cpu: Math.min(100, spike),
      memory: Math.min(100, spike * 0.85),
      latency: 100 + spike * 25,
      errorRate: 0.5 + i * 2.5,
    }
  })
  return [...history, ...spikes]
}

export const INITIAL_ALERTS: Alert[] = [
  {
    id: 'a1',
    service: 'auth-service',
    severity: 'warning',
    message: 'CPU usage at 72% — approaching threshold. ML model predicts 67% failure probability.',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    acknowledged: false,
  },
  {
    id: 'a2',
    service: 'auth-service',
    severity: 'warning',
    message: 'Elevated restart count detected (2 restarts in last 1h). OOMKill suspected.',
    timestamp: new Date(Date.now() - 240000).toISOString(),
    acknowledged: false,
  },
  {
    id: 'a3',
    service: 'payment-service',
    severity: 'info',
    message: 'Latency P99 at 120ms. Within acceptable range.',
    timestamp: new Date(Date.now() - 360000).toISOString(),
    acknowledged: true,
  },
]

export const AI_INSIGHTS: AIInsight[] = [
  {
    id: 'i1',
    title: 'Cascading Failure Risk Detected',
    description: 'auth-service at 67% failure probability. If it fails, payment-service will lose authentication capability within 30–60 seconds.',
    action: 'Scale auth-service to 4 replicas and increase memory limit from 512Mi to 1Gi.',
    severity: 'critical',
    confidence: 91,
  },
  {
    id: 'i2',
    title: 'Memory Leak Pattern',
    description: 'auth-service memory growth rate suggests OOMKill within 2 hours. Pattern matches known Node.js event listener leak signature.',
    action: 'kubectl rollout restart deployment/auth-service && review EventEmitter cleanup in auth handlers.',
    severity: 'warning',
    confidence: 84,
  },
  {
    id: 'i3',
    title: 'Traffic Spike Anticipated',
    description: 'Historical patterns show 3x traffic increase in next 45 minutes (business hours peak).',
    action: 'Pre-scale notification-service to 4 replicas before peak window.',
    severity: 'info',
    confidence: 76,
  },
]

export function getClusterHealth(services: ServiceMetrics[]): ClusterHealth {
  const healthy = services.filter(s => s.status === 'healthy').length
  const warning = services.filter(s => s.status === 'warning').length
  const critical = services.filter(s => s.status === 'critical' || s.status === 'failed').length
  const score = Math.round((healthy / services.length) * 100 - warning * 10 - critical * 25)

  return {
    overallScore: Math.max(0, score),
    healthyServices: healthy,
    warningServices: warning,
    criticalServices: critical,
    totalPods: services.reduce((a, s) => a + s.replicas, 0),
    runningPods: services.reduce((a, s) => a + (s.status !== 'failed' ? s.replicas : 0), 0),
    pendingPods: critical > 0 ? 2 : 0,
  }
}

export const SIMULATION_PHASES = {
  payment: {
    affected: ['auth-service', 'notification-service'],
    messages: [
      '⚡ payment-service: Connection timeout — pod CrashLoopBackOff',
      '🔴 auth-service: Upstream dependency UNAVAILABLE',
      '🔴 notification-service: Queue processor — dependency lost',
      '⚠️ Circuit breaker OPEN on payment→auth route',
      '📊 Error rate spike: 0.2% → 48.7%',
      '🚨 SLA breach detected — P99 latency > 5000ms',
    ],
  },
  auth: {
    affected: ['payment-service', 'user-service'],
    messages: [
      '⚡ auth-service: OOMKill — pod evicted',
      '🔴 payment-service: Auth validation FAILED — transactions blocked',
      '🔴 user-service: Session invalidation cascade triggered',
      '⚠️ JWT verification unavailable — 100% auth failure rate',
      '📊 Failed requests: 0 → 1,203/sec',
      '🚨 Revenue impact: ~$12,000/min estimated',
    ],
  },
}

export const CASCADE_AI_INSIGHTS: AIInsight[] = [
  {
    id: 'c1',
    title: '🚨 CRITICAL: Cascading Failure Detected',
    description: 'Primary failure in payment-service has triggered blast radius expansion to 2 downstream services. 73% of user traffic now impacted.',
    action: 'IMMEDIATE: kubectl rollout restart deployment/payment-service -n production',
    severity: 'critical',
    confidence: 98,
  },
  {
    id: 'c2',
    title: 'Circuit Breaker Recommendation',
    description: 'Implement circuit breaker pattern between payment-service and auth-service to prevent cascading on future failures.',
    action: 'Deploy Istio service mesh with circuit breaker policy: 5xx threshold = 50%, trip duration = 30s',
    severity: 'critical',
    confidence: 95,
  },
  {
    id: 'c3',
    title: 'Auto-Recovery Initiated',
    description: 'Kubernetes self-healing detected. New pod scheduling in progress. ETA to recovery: 45–90 seconds.',
    action: 'Monitor restart count. If >5 in 10min, check resource quotas and node capacity.',
    severity: 'warning',
    confidence: 88,
  },
]
