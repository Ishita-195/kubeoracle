import { motion } from 'framer-motion'
import { Shield, Layers, TrendingUp, Activity } from 'lucide-react'
import type { ClusterHealth } from '../types'

interface ClusterOverviewProps {
  health: ClusterHealth
  isSimulating: boolean
}

export function ClusterOverview({ health, isSimulating }: ClusterOverviewProps) {
  const score = isSimulating ? Math.max(30, health.overallScore - 35) : health.overallScore
  const scoreColor = score >= 80 ? '#34d399' : score >= 50 ? '#fbbf24' : '#ef4444'

  const stats = [
    {
      label: 'Health Score',
      value: `${score}%`,
      icon: Shield,
      color: scoreColor,
      desc: score >= 80 ? 'All systems nominal' : score >= 50 ? 'Degraded performance' : 'CRITICAL STATE',
    },
    {
      label: 'Active Pods',
      value: `${isSimulating ? health.runningPods - 2 : health.runningPods}/${health.totalPods}`,
      icon: Layers,
      color: '#06b6d4',
      desc: `${health.pendingPods + (isSimulating ? 2 : 0)} pending`,
    },
    {
      label: 'Avg Latency',
      value: isSimulating ? '2.4s' : '119ms',
      icon: Activity,
      color: isSimulating ? '#ef4444' : '#34d399',
      desc: isSimulating ? '20x above baseline' : 'P99 within SLA',
    },
    {
      label: 'Request Rate',
      value: isSimulating ? '846/s' : '2,846/s',
      icon: TrendingUp,
      color: isSimulating ? '#ef4444' : '#06b6d4',
      desc: isSimulating ? 'Traffic dropped 70%' : 'Normal throughput',
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4 mb-5">
      {stats.map((stat, i) => {
        const Icon = stat.icon
        return (
          <motion.div
            key={stat.label}
            className="glass-card rounded-xl p-4 relative overflow-hidden"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <div
              className="absolute top-0 left-0 right-0 h-[1px]"
              style={{ background: `linear-gradient(90deg, transparent, ${stat.color}44, transparent)` }}
            />
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] text-white/30 font-mono uppercase tracking-widest mb-1">{stat.label}</p>
                <motion.p
                  className="font-display text-2xl font-bold"
                  style={{ color: stat.color }}
                  animate={isSimulating && stat.label === 'Health Score' ? { opacity: [1, 0.7, 1] } : {}}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  {stat.value}
                </motion.p>
                <p className="text-[10px] text-white/30 font-mono mt-1">{stat.desc}</p>
              </div>
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${stat.color}15`, border: `1px solid ${stat.color}30` }}
              >
                <Icon className="w-4 h-4" style={{ color: stat.color }} />
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
