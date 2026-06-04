import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'
import { motion } from 'framer-motion'
import type { MetricHistory } from '../types'

interface MetricsChartProps {
  data: MetricHistory[]
  isSimulating?: boolean
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card px-3 py-2 text-[11px] font-mono">
      <div className="text-white/40 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex justify-between gap-3">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-white font-bold">{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</span>
        </div>
      ))}
    </div>
  )
}

export function CpuMemChart({ data, isSimulating }: MetricsChartProps) {
  return (
    <motion.div
      animate={isSimulating ? { filter: ['brightness(1)', 'brightness(1.3)', 'brightness(1)'] } : {}}
      transition={{ duration: 1, repeat: Infinity }}
      className="w-full h-36"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isSimulating ? '#ef4444' : '#06b6d4'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isSimulating ? '#ef4444' : '#06b6d4'} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={{ fill: '#374151', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} tick={{ fill: '#374151', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Area type="monotone" dataKey="cpu" name="CPU %" stroke={isSimulating ? '#ef4444' : '#06b6d4'} strokeWidth={2} fill="url(#cpuGrad)" dot={false} />
          <Area type="monotone" dataKey="memory" name="MEM %" stroke="#8b5cf6" strokeWidth={1.5} fill="url(#memGrad)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  )
}

export function LatencyChart({ data, isSimulating }: MetricsChartProps) {
  return (
    <motion.div
      animate={isSimulating ? { filter: ['brightness(1)', 'brightness(1.4)', 'brightness(1)'] } : {}}
      transition={{ duration: 0.8, repeat: Infinity }}
      className="w-full h-36"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={{ fill: '#374151', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#374151', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="latency" name="Latency (ms)" stroke={isSimulating ? '#ef4444' : '#34d399'} strokeWidth={2} dot={false} strokeDasharray={isSimulating ? '0' : '0'} />
          <Line type="monotone" dataKey="errorRate" name="Error Rate %" stroke="#f97316" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  )
}
