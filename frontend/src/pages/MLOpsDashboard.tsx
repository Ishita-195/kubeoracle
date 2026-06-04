import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
  Cpu, Database, Zap, BarChart2, RefreshCw, Clock, Target,
  GitBranch, Server, Layers, ChevronRight,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const BASE = '/api/mlops'

async function fetchJSON(url: string) {
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(3000) })
    if (!r.ok) throw new Error('bad response')
    return await r.json()
  } catch {
    return null
  }
}

// ─── Colour helpers ──────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  healthy: '#34d399',
  warning: '#fbbf24',
  degraded: '#f97316',
  critical: '#ef4444',
  stable: '#34d399',
  warning_drift: '#fbbf24',
  critical_drift: '#ef4444',
  improving: '#34d399',
  declining: '#ef4444',
}

function statusColor(s: string) { return STATUS_COLORS[s] ?? '#60a5fa' }

// ─── Tiny sub-components ─────────────────────────────────────────────────────
function KV({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-mono uppercase tracking-widest text-white/30">{label}</span>
      <span className="font-mono text-sm font-bold" style={{ color: color ?? '#e2e8f0' }}>{value}</span>
    </div>
  )
}

function SectionTitle({ icon: Icon, title }: { icon: any; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-3.5 h-3.5 text-cyan-400" />
      <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">{title}</h2>
    </div>
  )
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider"
      style={{ background: color + '22', color, border: `1px solid ${color}44` }}
    >
      {label}
    </span>
  )
}

function MetricCard({ title, value, sub, icon: Icon, trend, color = '#34d399' }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-xl p-4 flex flex-col gap-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-widest text-white/35">{title}</span>
        <Icon className="w-3.5 h-3.5 text-white/20" />
      </div>
      <div className="flex items-end gap-2">
        <span className="font-mono text-2xl font-bold" style={{ color }}>{value}</span>
        {trend && (
          trend === 'improving' ? <TrendingUp className="w-4 h-4 text-emerald-400 mb-1" />
            : trend === 'declining' ? <TrendingDown className="w-4 h-4 text-red-400 mb-1" />
              : null
        )}
      </div>
      {sub && <span className="text-[10px] text-white/25 font-mono">{sub}</span>}
    </motion.div>
  )
}

// ─── Skeleton loader ─────────────────────────────────────────────────────────
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`bg-white/5 animate-pulse rounded ${className}`} />
}

// ─── Feature importance bar ──────────────────────────────────────────────────
function FeatureBar({ name, importance, max }: { name: string; importance: number; max: number }) {
  const pct = (importance / max) * 100
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] font-mono text-white/50 w-32 truncate">{name}</span>
      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-cyan-400"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="text-[10px] font-mono text-white/40 w-10 text-right">
        {(importance * 100).toFixed(1)}%
      </span>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function MLOpsDashboard() {
  const [perf, setPerf] = useState<any>(null)
  const [latency, setLatency] = useState<any>(null)
  const [features, setFeatures] = useState<any>(null)
  const [drift, setDrift] = useState<any>(null)
  const [driftQuality, setDriftQuality] = useState<any>(null)
  const [training, setTraining] = useState<any>(null)
  const [pipelineHealth, setPipelineHealth] = useState<any>(null)
  const [sysHealth, setSysHealth] = useState<any>(null)
  const [sysResources, setSysResources] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const load = async () => {
    setLoading(true)
    const [p, l, f, d, dq, t, ph, sh, sr] = await Promise.all([
      fetchJSON(`${BASE}/model-performance/summary?hours=24`),
      fetchJSON(`${BASE}/model-performance/latency-stats?hours=24`),
      fetchJSON(`${BASE}/model-performance/feature-importance`),
      fetchJSON(`${BASE}/data-drift/summary?hours=24`),
      fetchJSON(`${BASE}/data-drift/quality?hours=24`),
      fetchJSON(`${BASE}/training/history?hours=72`),
      fetchJSON(`${BASE}/training/pipeline-health`),
      fetchJSON(`${BASE}/system/health`),
      fetchJSON(`${BASE}/system/resources?hours=24`),
    ])
    setPerf(p); setLatency(l); setFeatures(f)
    setDrift(d); setDriftQuality(dq)
    setTraining(t); setPipelineHealth(ph)
    setSysHealth(sh); setSysResources(sr)
    setLoading(false)
    setLastRefresh(new Date())
  }

  useEffect(() => { load() }, [])

  // ── Feature importance data ───────────────────────────────────────────────
  const featureList: any[] = features?.features ?? []
  const maxImportance = featureList[0]?.importance ?? 1

  // ── Drift feature list ────────────────────────────────────────────────────
  const driftFeatures = Object.entries(drift?.features ?? {}) as [string, any][]

  // ── Sparkline mock data (real app would store history) ────────────────────
  const sparkData = Array.from({ length: 20 }, (_, i) => ({
    i,
    v: 0.88 + Math.sin(i * 0.4) * 0.03 + Math.random() * 0.01,
  }))

  const latencySpark = Array.from({ length: 20 }, (_, i) => ({
    i,
    v: 45 + Math.sin(i * 0.6) * 12 + Math.random() * 5,
  }))

  const cpuData = Array.from({ length: 20 }, (_, i) => ({
    i,
    cpu: sysResources?.cpu?.mean ?? 45 + Math.sin(i * 0.5) * 15,
    mem: sysResources?.memory?.mean ?? 60 + Math.cos(i * 0.4) * 10,
  }))

  return (
    <div className="flex flex-col gap-5 px-6 py-5 overflow-auto min-h-0">

      {/* ── Header row ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold text-white tracking-widest">
            ML<span className="text-cyan-400">OPS</span> DASHBOARDS
          </h1>
          <p className="text-[11px] text-white/30 font-mono mt-0.5">
            Model performance · Data drift · Training pipeline · System health
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/4 border border-white/8 text-[11px] font-mono text-white/40 hover:text-cyan-400 hover:border-cyan-500/30 transition-all"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          {lastRefresh.toLocaleTimeString()}
        </button>
      </div>

      {/* ── Top KPI strip ── */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          title="Model Accuracy"
          value={perf?.accuracy ? `${(perf.accuracy * 100).toFixed(1)}%` : '—'}
          sub={`F1: ${perf?.f1_score ? (perf.f1_score * 100).toFixed(1) + '%' : '—'}`}
          icon={Target}
          trend={perf?.trend}
          color={perf?.accuracy >= 0.9 ? '#34d399' : perf?.accuracy >= 0.8 ? '#fbbf24' : '#ef4444'}
        />
        <MetricCard
          title="P95 Latency"
          value={latency?.p95_ms ? `${latency.p95_ms.toFixed(0)}ms` : '—'}
          sub={`mean ${latency?.mean_ms?.toFixed(0) ?? '—'}ms`}
          icon={Zap}
          color={latency?.p95_ms < 200 ? '#34d399' : '#fbbf24'}
        />
        <MetricCard
          title="Training Runs (72h)"
          value={training?.total_runs ?? '—'}
          sub={`${training?.completed_runs ?? '—'} completed · ${training?.failed_runs ?? '—'} failed`}
          icon={GitBranch}
          color="#60a5fa"
        />
        <MetricCard
          title="System Status"
          value={sysHealth?.overall_status ?? '—'}
          sub={`CPU ${sysResources?.cpu?.latest?.toFixed(0) ?? '—'}%  Mem ${sysResources?.memory?.latest?.toFixed(0) ?? '—'}%`}
          icon={Server}
          color={statusColor(sysHealth?.overall_status ?? 'healthy')}
        />
      </div>

      {/* ── Row 2: Performance + Drift ── */}
      <div className="grid grid-cols-2 gap-4">

        {/* Model Performance */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-4">
          <SectionTitle icon={Activity} title="Model Performance" />

          <div className="grid grid-cols-3 gap-3">
            {[
              { l: 'Accuracy', v: perf?.accuracy },
              { l: 'Precision', v: perf?.precision },
              { l: 'Recall', v: perf?.recall },
              { l: 'F1 Score', v: perf?.f1_score },
              { l: 'AUC-ROC', v: perf?.auc_roc },
              { l: 'Evaluations', v: perf?.n_evaluations, raw: true },
            ].map(({ l, v, raw }) => (
              <KV
                key={l}
                label={l}
                value={v == null ? '—' : raw ? v : `${(v * 100).toFixed(2)}%`}
                color={v != null && !raw ? statusColor(v >= 0.9 ? 'healthy' : v >= 0.8 ? 'warning' : 'critical') : undefined}
              />
            ))}
          </div>

          {/* Accuracy sparkline */}
          <div>
            <span className="text-[10px] font-mono text-white/25 uppercase tracking-wider">Accuracy trend (24 h)</span>
            <ResponsiveContainer width="100%" height={50}>
              <AreaChart data={sparkData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="v" stroke="#34d399" strokeWidth={1.5} fill="url(#accGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Data Drift */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">Data Drift (PSI)</h2>
            </div>
            <div className="flex gap-2">
              <Badge label={`${drift?.alerts?.critical ?? 0} critical`} color="#ef4444" />
              <Badge label={`${drift?.alerts?.warning ?? 0} warn`} color="#fbbf24" />
            </div>
          </div>

          <div className="flex flex-col gap-2 flex-1 overflow-y-auto">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8" />)
            ) : driftFeatures.length === 0 ? (
              <p className="text-xs text-white/25 font-mono italic">No drift data yet.</p>
            ) : (
              driftFeatures.map(([name, data]) => (
                <div key={name} className="flex items-center gap-3 py-1 border-b border-white/4">
                  <span className="text-[11px] font-mono text-white/60 w-28 truncate">{name}</span>
                  <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: statusColor(data.drift_status) }}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, (data.latest_psi / 0.3) * 100)}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <span className="text-[10px] font-mono w-12 text-right" style={{ color: statusColor(data.drift_status) }}>
                    {data.latest_psi?.toFixed(3)}
                  </span>
                  <Badge label={data.drift_status.replace('_drift', '')} color={statusColor(data.drift_status)} />
                </div>
              ))
            )}
          </div>

          {/* Data quality strip */}
          <div className="border-t border-white/5 pt-2 grid grid-cols-3 gap-2">
            <KV label="Samples" value={driftQuality?.total_samples?.toLocaleString() ?? '—'} />
            <KV label="Missing %" value={driftQuality?.avg_missing_rate != null ? `${(driftQuality.avg_missing_rate * 100).toFixed(1)}%` : '—'} />
            <KV label="Outlier %" value={driftQuality?.avg_outlier_rate != null ? `${(driftQuality.avg_outlier_rate * 100).toFixed(2)}%` : '—'} />
          </div>
        </div>
      </div>

      {/* ── Row 3: Latency + Feature Importance + Training + System ── */}
      <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-4">

        {/* Latency */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-3">
          <SectionTitle icon={Zap} title="Inference Latency" />
          <div className="grid grid-cols-2 gap-2">
            {[
              { l: 'Mean', v: latency?.mean_ms },
              { l: 'Median', v: latency?.median_ms },
              { l: 'P95', v: latency?.p95_ms },
              { l: 'P99', v: latency?.p99_ms },
            ].map(({ l, v }) => (
              <KV
                key={l}
                label={l}
                value={v != null ? `${v.toFixed(0)}ms` : '—'}
                color={v != null ? (v < 200 ? '#34d399' : v < 500 ? '#fbbf24' : '#ef4444') : undefined}
              />
            ))}
          </div>
          <ResponsiveContainer width="100%" height={50}>
            <AreaChart data={latencySpark} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="#60a5fa" strokeWidth={1.5} fill="url(#latGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <KV label="Samples" value={latency?.n_samples ?? '—'} />
        </div>

        {/* Feature Importance */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-3">
          <SectionTitle icon={BarChart2} title="Feature Importance" />
          <div className="flex flex-col gap-2 flex-1">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-4" />)
            ) : featureList.length === 0 ? (
              <p className="text-xs text-white/25 font-mono italic">No data yet.</p>
            ) : (
              featureList.slice(0, 6).map((f: any) => (
                <FeatureBar key={f.name} name={f.name} importance={f.importance} max={maxImportance} />
              ))
            )}
          </div>
        </div>

        {/* Training Pipeline */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-3">
          <SectionTitle icon={GitBranch} title="Training Pipeline" />

          <div className="grid grid-cols-2 gap-2">
            <KV label="Total Runs" value={training?.total_runs ?? '—'} />
            <KV label="Success Rate" value={training?.success_rate != null ? `${(training.success_rate * 100).toFixed(0)}%` : '—'}
              color={training?.success_rate >= 0.95 ? '#34d399' : '#fbbf24'} />
            <KV label="Best Val Loss" value={training?.best_val_loss?.toFixed(4) ?? '—'} color="#60a5fa" />
            <KV label="Avg Duration" value={training?.avg_duration_seconds ? `${Math.round(training.avg_duration_seconds)}s` : '—'} />
          </div>

          <div className="border-t border-white/5 pt-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-white/25">Pipeline Health</span>
            <div className="flex items-center gap-2 mt-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ background: statusColor(pipelineHealth?.overall_health ?? 'healthy') }}
              />
              <span className="text-xs font-mono capitalize" style={{ color: statusColor(pipelineHealth?.overall_health ?? 'healthy') }}>
                {pipelineHealth?.overall_health ?? 'unknown'}
              </span>
            </div>
          </div>

          {training?.latest_run && (
            <div className="border-t border-white/5 pt-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-white/25">Latest Run</span>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[11px] font-mono text-white/60">{training.latest_run.run_id}</span>
                <Badge
                  label={training.latest_run.status}
                  color={training.latest_run.status === 'completed' ? '#34d399' : '#ef4444'}
                />
              </div>
            </div>
          )}
        </div>

        {/* System Health */}
        <div className="glass-card rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <h2 className="text-[11px] font-mono font-bold text-white/40 uppercase tracking-widest">System Health</h2>
            </div>
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: statusColor(sysHealth?.overall_status ?? 'healthy') }}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <KV label="CPU %" value={sysResources?.cpu?.latest != null ? `${sysResources.cpu.latest.toFixed(0)}%` : '—'}
              color={sysResources?.cpu?.latest < 75 ? '#34d399' : '#fbbf24'} />
            <KV label="Memory %" value={sysResources?.memory?.latest != null ? `${sysResources.memory.latest.toFixed(0)}%` : '—'}
              color={sysResources?.memory?.latest < 85 ? '#34d399' : '#ef4444'} />
            <KV label="GPU Mem" value={sysResources?.gpu_memory_mb?.latest ? `${(sysResources.gpu_memory_mb.latest / 1024).toFixed(1)}GB` : '—'} />
            <KV label="GPU Util" value={sysResources?.gpu_utilization?.latest != null ? `${sysResources.gpu_utilization.latest.toFixed(0)}%` : '—'} />
          </div>

          <ResponsiveContainer width="100%" height={50}>
            <LineChart data={cpuData} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <Line type="monotone" dataKey="cpu" stroke="#34d399" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="mem" stroke="#60a5fa" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>

          <div className="flex gap-3 text-[10px] font-mono text-white/30">
            <span className="flex items-center gap-1"><span className="w-2 h-px bg-emerald-400 inline-block" /> CPU</span>
            <span className="flex items-center gap-1"><span className="w-2 h-px bg-blue-400 inline-block" /> MEM</span>
          </div>

          {/* Sub-component health */}
          {sysHealth && (
            <div className="border-t border-white/5 pt-2 flex flex-col gap-1">
              {[
                { label: 'CPU', v: sysHealth.resources?.cpu_health },
                { label: 'Memory', v: sysHealth.resources?.memory_health },
                { label: 'Endpoints', v: sysHealth.endpoints?.status },
                { label: 'Errors', v: sysHealth.errors?.status },
              ].map(({ label, v }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-white/30">{label}</span>
                  <span className="text-[10px] font-mono capitalize" style={{ color: statusColor(v ?? 'healthy') }}>{v ?? '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
