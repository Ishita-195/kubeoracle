import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { Header } from '../components/Header'
import { ServiceCard } from '../components/ServiceCard'
import { DependencyGraph } from '../components/DependencyGraph'
import { CpuMemChart, LatencyChart } from '../components/MetricsChart'
import { AlertFeed } from '../components/AlertFeed'
import { AIInsightPanel } from '../components/AIInsightPanel'
import { SimulationBanner } from '../components/SimulationBanner'
import { ClusterOverview } from '../components/ClusterOverview'
import {
  SERVICES,
  INITIAL_ALERTS,
  AI_INSIGHTS,
  CASCADE_AI_INSIGHTS,
  SIMULATION_PHASES,
  generateMetricHistory,
  generateSpikedHistory,
  getClusterHealth,
} from '../lib/mockData'
import type { ServiceMetrics, Alert, AIInsight, SimulationState, MetricHistory } from '../types'

const TICK_INTERVAL = 3000 // 3 second live update

export function Dashboard() {
  const [services, setServices] = useState<ServiceMetrics[]>(SERVICES)
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_ALERTS)
  const [insights, setInsights] = useState<AIInsight[]>(AI_INSIGHTS)
  const [selectedService, setSelectedService] = useState<string>('payment-service')
  const [simulation, setSimulation] = useState<SimulationState>({
    active: false, failedService: null, affectedServices: [], phase: 'idle', progress: 0,
  })
  const [simLogs, setSimLogs] = useState<string[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const [metricHistory, setMetricHistory] = useState<Record<string, MetricHistory[]>>({})
  const [connected] = useState(false)
  const simTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Init metric histories
  useEffect(() => {
    const hist: Record<string, MetricHistory[]> = {}
    SERVICES.forEach(s => { hist[s.id] = generateMetricHistory(s.cpu, 20) })
    setMetricHistory(hist)
  }, [])

  // Live metric ticking
  useEffect(() => {
    const interval = setInterval(() => {
      if (simulation.active) return
      setMetricHistory(prev => {
        const next = { ...prev }
        SERVICES.forEach(s => {
          const last = prev[s.id] || []
          const jitter = (Math.random() - 0.5) * 8
          const newPoint = {
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            cpu: Math.min(100, Math.max(0, s.cpu + jitter)),
            memory: Math.min(100, Math.max(0, s.memory + jitter * 0.6)),
            latency: Math.max(10, s.latency + jitter * 5),
            errorRate: Math.max(0, s.errorRate + jitter * 0.02),
          }
          next[s.id] = [...last.slice(-19), newPoint]
        })
        return next
      })
    }, TICK_INTERVAL)
    return () => clearInterval(interval)
  }, [simulation.active])

  const addAlert = useCallback((alert: Omit<Alert, 'id'>) => {
    setAlerts(prev => [{
      ...alert,
      id: `alert-${Date.now()}-${Math.random()}`,
    }, ...prev])
  }, [])

  const addSimLog = useCallback((msg: string) => {
    setSimLogs(prev => [...prev, msg])
  }, [])

  const runSimulation = useCallback(async (serviceId: string) => {
    if (simulation.active) return

    const phases = SIMULATION_PHASES[serviceId as keyof typeof SIMULATION_PHASES]
    if (!phases) return

    setSimLogs([])
    setSimulation({ active: true, failedService: serviceId, affectedServices: [], phase: 'initiating', progress: 5 })
    setAiLoading(true)

    // Phase 1: Initiating (0-20%)
    await delay(600)
    addSimLog(phases.messages[0])
    setSimulation(s => ({ ...s, progress: 20 }))

    addAlert({
      service: serviceId,
      severity: 'critical',
      message: `🚨 CRITICAL: ${serviceId} is entering CrashLoopBackOff state. Pod eviction triggered.`,
      timestamp: new Date().toISOString(),
      acknowledged: false,
    })

    // Spike the metrics for failed service
    setMetricHistory(prev => ({
      ...prev,
      [serviceId]: generateSpikedHistory(85, 20),
    }))

    // Phase 2: Propagating (20-50%)
    await delay(800)
    setSimulation(s => ({ ...s, phase: 'propagating', affectedServices: [phases.affected[0]], progress: 40 }))
    addSimLog(phases.messages[1])
    addSimLog(phases.messages[2])

    addAlert({
      service: phases.affected[0],
      severity: 'critical',
      message: `CASCADE: ${phases.affected[0]} lost upstream dependency. Entering degraded state.`,
      timestamp: new Date().toISOString(),
      acknowledged: false,
    })

    // Phase 3: Cascading (50-80%)
    await delay(1000)
    setSimulation(s => ({
      ...s,
      phase: 'cascading',
      affectedServices: phases.affected,
      progress: 65,
    }))
    addSimLog(phases.messages[3])
    addSimLog(phases.messages[4])
    addSimLog(phases.messages[5])

    if (phases.affected[1]) {
      addAlert({
        service: phases.affected[1],
        severity: 'warning',
        message: `BLAST RADIUS: ${phases.affected[1]} degraded due to cascading failure from ${serviceId}.`,
        timestamp: new Date().toISOString(),
        acknowledged: false,
      })
    }

    // Spike affected services
    phases.affected.forEach(affId => {
      setMetricHistory(prev => ({
        ...prev,
        [affId]: generateSpikedHistory(60, 20),
      }))
    })

    await delay(600)
    setSimulation(s => ({ ...s, progress: 80 }))

    // AI insights load in
    setAiLoading(false)
    setInsights(CASCADE_AI_INSIGHTS)

    // Phase 4: Show final state (80-100%)
    await delay(1200)
    setSimulation(s => ({ ...s, phase: 'recovering', progress: 100 }))
    addSimLog('🔄 Kubernetes self-healing: scheduling replacement pod...')
    addAlert({
      service: serviceId,
      severity: 'info',
      message: `Self-healing: New pod scheduled for ${serviceId}. ETA ~45s.`,
      timestamp: new Date().toISOString(),
      acknowledged: false,
    })

  }, [simulation.active, addAlert, addSimLog])

  const resetSimulation = useCallback(() => {
    setSimulation({ active: false, failedService: null, affectedServices: [], phase: 'idle', progress: 0 })
    setSimLogs([])
    setInsights(AI_INSIGHTS)
    const hist: Record<string, MetricHistory[]> = {}
    SERVICES.forEach(s => { hist[s.id] = generateMetricHistory(s.cpu, 20) })
    setMetricHistory(hist)
  }, [])

  const dismissAlert = useCallback((id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a))
  }, [])

  const health = getClusterHealth(services)
  const activeAlertCount = alerts.filter(a => !a.acknowledged).length
  const selectedMetrics = metricHistory[selectedService] || []
  const selectedSvc = services.find(s => s.id === selectedService)

  return (
    <div className="min-h-screen flex flex-col overflow-hidden">
      <Header
        health={health}
        alertCount={activeAlertCount}
        connected={connected}
      />

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-5 flex flex-col gap-0 overflow-auto">

        {/* Simulation banner */}
        <SimulationBanner simulation={simulation} logs={simLogs} />

        {/* Overview stats */}
        <ClusterOverview health={health} isSimulating={simulation.active} />

        {/* Main 3-col layout */}
        <div className="grid grid-cols-[280px_1fr_300px] gap-4 flex-1 min-h-0">

          {/* LEFT: Service cards */}
          <div className="flex flex-col gap-3 overflow-y-auto pr-1">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">Services</h2>
              <span className="text-[10px] font-mono text-white/20">{services.length} total</span>
            </div>
            {services.map(s => (
              <ServiceCard
                key={s.id}
                service={s}
                isSelected={selectedService === s.id}
                isSimulating={simulation.active}
                isFailed={simulation.failedService === s.id}
                isAffected={simulation.affectedServices.includes(s.id)}
                onClick={() => setSelectedService(s.id)}
                onSimulate={runSimulation}
              />
            ))}

            {/* Reset button */}
            {simulation.active && simulation.progress >= 80 && (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-2 w-full py-2 rounded-lg text-[11px] font-mono font-bold uppercase tracking-wider bg-white/4 border border-white/10 text-white/40 hover:bg-emerald-500/15 hover:border-emerald-500/40 hover:text-emerald-300 transition-all"
                onClick={resetSimulation}
              >
                ↺ Reset Simulation
              </motion.button>
            )}
          </div>

          {/* CENTER: Graph + Charts */}
          <div className="flex flex-col gap-4 min-h-0 overflow-hidden">

            {/* Dependency graph */}
            <div className="glass-card rounded-xl overflow-hidden flex-1 min-h-[280px] relative">
              <div className="absolute top-3 left-4 z-10">
                <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">
                  Service Dependency Graph
                </h2>
              </div>
              <DependencyGraph
                services={services}
                failedService={simulation.failedService}
                affectedServices={simulation.affectedServices}
              />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-card rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">CPU / Memory</h3>
                  <span className="text-[10px] font-mono text-white/20">{selectedService}</span>
                </div>
                <CpuMemChart data={selectedMetrics} isSimulating={simulation.failedService === selectedService || simulation.affectedServices.includes(selectedService)} />
              </div>
              <div className="glass-card rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">Latency / Error Rate</h3>
                  <span className="text-[10px] font-mono text-white/20">{selectedService}</span>
                </div>
                <LatencyChart data={selectedMetrics} isSimulating={simulation.failedService === selectedService || simulation.affectedServices.includes(selectedService)} />
              </div>
            </div>
          </div>

          {/* RIGHT: Alerts + AI */}
          <div className="flex flex-col gap-4 min-h-0 overflow-hidden">

            {/* Alerts */}
            <div className="glass-card rounded-xl p-4 flex-shrink-0 max-h-[300px] overflow-hidden flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">Live Alerts</h2>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${activeAlertCount > 0 ? 'bg-red-500/20 text-red-400' : 'bg-white/5 text-white/20'}`}>
                  {activeAlertCount} active
                </span>
              </div>
              <div className="overflow-y-auto flex-1">
                <AlertFeed alerts={alerts} onDismiss={dismissAlert} />
              </div>
            </div>

            {/* AI Panel */}
            <div className="glass-card-cyan rounded-xl p-4 flex-1 min-h-0 overflow-hidden flex flex-col">
              <AIInsightPanel
                insights={insights}
                isLoading={aiLoading}
                simulationActive={simulation.active}
                failedService={simulation.failedService}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
