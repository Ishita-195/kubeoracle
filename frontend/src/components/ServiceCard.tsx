import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, MemoryStick, RefreshCw, Clock, Zap, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '../lib/utils'
import type { ServiceMetrics } from '../types'

interface ServiceCardProps {
  service: ServiceMetrics
  isSelected: boolean
  isSimulating: boolean
  isFailed: boolean
  isAffected: boolean
  onClick: () => void
  onSimulate: (id: string) => void
}

const STATUS_CONFIG = {
  healthy: {
    label: 'HEALTHY',
    color: '#34d399',
    bg: 'rgba(52, 211, 153, 0.08)',
    border: 'rgba(52, 211, 153, 0.2)',
    icon: CheckCircle2,
    pulse: 'status-pulse-green',
  },
  warning: {
    label: 'WARNING',
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.08)',
    border: 'rgba(251, 191, 36, 0.2)',
    icon: AlertTriangle,
    pulse: '',
  },
  critical: {
    label: 'CRITICAL',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.08)',
    border: 'rgba(239, 68, 68, 0.25)',
    icon: AlertTriangle,
    pulse: 'status-pulse-red',
  },
  failed: {
    label: 'FAILED',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    border: 'rgba(239, 68, 68, 0.4)',
    icon: XCircle,
    pulse: 'status-pulse-red',
  },
}

export function ServiceCard({ service, isSelected, isSimulating, isFailed, isAffected, onClick, onSimulate }: ServiceCardProps) {
  const statusKey = isFailed ? 'failed' : isAffected ? 'critical' : service.status
  const config = STATUS_CONFIG[statusKey] || STATUS_CONFIG.healthy
  const Icon = config.icon

  const displayCpu = isFailed ? 98 : isAffected ? service.cpu + 30 : service.cpu
  const displayMem = isFailed ? 97 : isAffected ? service.memory + 20 : service.memory
  const displayLatency = isFailed ? 9999 : isAffected ? service.latency * 8 : service.latency
  const displayError = isFailed ? 94.7 : isAffected ? service.errorRate * 15 : service.errorRate

  const failProb = isFailed ? 100 : isAffected ? 89 : service.failureProbability
  const probColor = failProb >= 70 ? '#ef4444' : failProb >= 40 ? '#fbbf24' : '#34d399'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: isFailed ? [1, 1.02, 0.98, 1] : 1,
      }}
      transition={{ duration: 0.3 }}
      onClick={onClick}
      className={cn(
        'relative rounded-xl cursor-pointer transition-all duration-300 overflow-hidden',
        isSelected && 'ring-1 ring-cyan-500/50',
        isFailed && 'border-glow-red',
        isAffected && !isFailed && 'border-glow-red',
      )}
      style={{
        background: isFailed || isAffected ? 'rgba(239,68,68,0.06)' : config.bg,
        border: `1px solid ${isFailed || isAffected ? 'rgba(239,68,68,0.3)' : config.border}`,
      }}
    >
      {/* Animated top bar */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px]"
        style={{
          background: isFailed || isAffected
            ? 'linear-gradient(90deg, transparent, #ef4444, transparent)'
            : `linear-gradient(90deg, transparent, ${config.color}, transparent)`,
        }}
      />

      {/* Failed overlay shimmer */}
      <AnimatePresence>
        {(isFailed || isAffected) && (
          <motion.div
            className="absolute inset-0 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.05, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{ background: 'radial-gradient(circle at 50% 50%, rgba(239,68,68,0.3), transparent 70%)' }}
          />
        )}
      </AnimatePresence>

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className={cn('w-2 h-2 rounded-full', config.pulse)} style={{ background: config.color }} />
              <span
                className="text-[10px] font-mono font-bold tracking-[0.15em] uppercase"
                style={{ color: config.color }}
              >
                {config.label}
              </span>
            </div>
            <h3 className="font-mono text-sm font-bold text-white">{service.name}</h3>
            <p className="text-[10px] text-white/30 font-mono mt-0.5">
              {service.replicas} replicas · {service.requestsPerSec.toLocaleString()} rps
            </p>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-white/30 font-mono mb-1">FAILURE RISK</div>
            <div className="font-display text-lg font-bold" style={{ color: probColor }}>
              {failProb}
              <span className="text-xs text-white/30">%</span>
            </div>
          </div>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <MetricBar label="CPU" value={displayCpu} icon={<Cpu className="w-3 h-3" />} isSpiking={isFailed || isAffected} />
          <MetricBar label="MEM" value={displayMem} icon={<MemoryStick className="w-3 h-3" />} isSpiking={isFailed || isAffected} />
        </div>

        {/* Bottom stats */}
        <div className="flex justify-between text-[10px] font-mono">
          <div className="flex items-center gap-1 text-white/40">
            <Clock className="w-3 h-3" />
            <span className={cn(displayLatency > 500 && 'text-red-400')}>
              {displayLatency > 1000 ? `${(displayLatency / 1000).toFixed(1)}s` : `${Math.round(displayLatency)}ms`}
            </span>
          </div>
          <div className="flex items-center gap-1 text-white/40">
            <RefreshCw className="w-3 h-3" />
            <span className={cn(service.restarts > 0 && 'text-amber-400')}>{service.restarts} restarts</span>
          </div>
          <div className="flex items-center gap-1 text-white/40">
            <Zap className="w-3 h-3" />
            <span className={cn(displayError > 5 && 'text-red-400')}>{displayError.toFixed(1)}% err</span>
          </div>
        </div>

        {/* Simulate button */}
        <motion.button
          className={cn(
            'mt-3 w-full py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider uppercase transition-all',
            isFailed
              ? 'bg-red-500/20 border border-red-500/40 text-red-300 cursor-not-allowed'
              : 'bg-white/4 border border-white/10 text-white/40 hover:bg-red-500/15 hover:border-red-500/40 hover:text-red-300'
          )}
          disabled={isSimulating || isFailed}
          onClick={(e) => { e.stopPropagation(); onSimulate(service.id) }}
          whileHover={{ scale: isSimulating || isFailed ? 1 : 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {isFailed ? '⚡ FAILED — SIMULATING' : isAffected ? '🔴 CASCADE AFFECTED' : `▶ Simulate Failure`}
        </motion.button>
      </div>
    </motion.div>
  )
}

function MetricBar({ label, value, icon, isSpiking }: { label: string; value: number; icon: React.ReactNode; isSpiking: boolean }) {
  const color = value >= 85 ? '#ef4444' : value >= 65 ? '#fbbf24' : '#34d399'
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1 text-white/30" style={{ fontSize: 10 }}>
          {icon}
          <span className="font-mono uppercase tracking-wider">{label}</span>
        </div>
        <span
          className={cn('text-[11px] font-mono font-bold', isSpiking && 'metric-spike')}
          style={{ color }}
        >
          {Math.min(100, Math.round(value))}%
        </span>
      </div>
      <div className="h-1 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          animate={{ width: `${Math.min(100, value)}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

import React from 'react'
