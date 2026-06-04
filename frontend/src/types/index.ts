export type ServiceStatus = 'healthy' | 'warning' | 'critical' | 'failed'

export interface ServiceMetrics {
  id: string
  name: string
  status: ServiceStatus
  cpu: number
  memory: number
  restarts: number
  latency: number
  errorRate: number
  failureProbability: number
  replicas: number
  requestsPerSec: number
  uptime: string
  dependencies: string[]
}

export interface MetricHistory {
  time: string
  cpu: number
  memory: number
  latency: number
  errorRate: number
}

export interface Alert {
  id: string
  service: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  timestamp: string
  acknowledged: boolean
}

export interface SimulationState {
  active: boolean
  failedService: string | null
  affectedServices: string[]
  phase: 'idle' | 'initiating' | 'propagating' | 'cascading' | 'recovering'
  progress: number
}

export interface AIInsight {
  id: string
  title: string
  description: string
  action: string
  severity: 'info' | 'warning' | 'critical'
  confidence: number
}

export interface ClusterHealth {
  overallScore: number
  healthyServices: number
  warningServices: number
  criticalServices: number
  totalPods: number
  runningPods: number
  pendingPods: number
}
