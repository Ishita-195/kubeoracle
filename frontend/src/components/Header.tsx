import { motion } from 'framer-motion'
import { Activity, Bell, Settings, Wifi, WifiOff } from 'lucide-react'
import type { ClusterHealth } from '../types'

interface HeaderProps {
  health: ClusterHealth
  alertCount: number
  connected: boolean
}

export function Header({ health, alertCount, connected }: HeaderProps) {
  const scoreColor =
    health.overallScore >= 80 ? '#34d399' : health.overallScore >= 50 ? '#fbbf24' : '#ef4444'

  return (
    <header className="relative z-50 border-b border-white/5 bg-black/30 backdrop-blur-xl">
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 status-pulse-green" />
          </div>
          <div>
            <h1 className="font-display text-lg font-bold tracking-widest text-white glow-cyan">
              KUBE<span className="text-cyan-400">ORACLE</span>
            </h1>
            <p className="text-[10px] text-white/30 font-mono tracking-[0.2em] uppercase">
              AI Observability Platform
            </p>
          </div>
        </motion.div>

        {/* Center - cluster score */}
        <motion.div
          className="flex items-center gap-6"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="text-center">
            <div className="text-[10px] text-white/30 font-mono uppercase tracking-widest mb-1">
              Cluster Health
            </div>
            <div className="font-display text-2xl font-bold" style={{ color: scoreColor }}>
              {health.overallScore}
              <span className="text-sm text-white/30">%</span>
            </div>
          </div>

          <div className="h-10 w-px bg-white/5" />

          <div className="flex gap-5 text-center">
            <Stat label="Running" value={`${health.runningPods}/${health.totalPods}`} color="#34d399" />
            <Stat label="Healthy" value={health.healthyServices} color="#34d399" />
            <Stat label="Warning" value={health.warningServices} color="#fbbf24" />
            <Stat label="Critical" value={health.criticalServices} color="#ef4444" />
          </div>
        </motion.div>

        {/* Right controls */}
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          {/* Connection indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/4 border border-white/8 text-xs font-mono">
            {connected ? (
              <>
                <Wifi className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400">LIVE</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-amber-400" />
                <span className="text-amber-400">MOCK</span>
              </>
            )}
          </div>

          {/* Alert bell */}
          <div className="relative cursor-pointer group">
            <div className="w-9 h-9 rounded-lg bg-white/4 border border-white/8 flex items-center justify-center transition-all group-hover:border-cyan-500/30 group-hover:bg-cyan-500/10">
              <Bell className="w-4 h-4 text-white/50 group-hover:text-cyan-400 transition-colors" />
            </div>
            {alertCount > 0 && (
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 flex items-center justify-center text-[9px] font-bold text-white status-pulse-red">
                {alertCount}
              </div>
            )}
          </div>

          <div className="w-9 h-9 rounded-lg bg-white/4 border border-white/8 flex items-center justify-center cursor-pointer hover:border-cyan-500/30 hover:bg-cyan-500/10 transition-all">
            <Settings className="w-4 h-4 text-white/50 hover:text-cyan-400 transition-colors" />
          </div>

          {/* Time */}
          <div className="px-3 py-1.5 rounded-lg bg-white/3 border border-white/6 font-mono text-xs text-white/40">
            <LiveClock />
          </div>
        </motion.div>
      </div>
    </header>
  )
}

function Stat({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div>
      <div className="text-[10px] text-white/30 font-mono uppercase tracking-widest mb-0.5">{label}</div>
      <div className="font-mono text-sm font-bold" style={{ color }}>{value}</div>
    </div>
  )
}

function LiveClock() {
  const [time, setTime] = React.useState(new Date())
  React.useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return <>{time.toLocaleTimeString()}</>
}

import React from 'react'
