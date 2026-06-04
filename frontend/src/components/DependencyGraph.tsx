import { useCallback, useEffect, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  MarkerType,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { motion } from 'framer-motion'
import type { ServiceMetrics } from '../types'

interface DependencyGraphProps {
  services: ServiceMetrics[]
  failedService: string | null
  affectedServices: string[]
}

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  'payment-service': { x: 100, y: 150 },
  'auth-service': { x: 350, y: 80 },
  'user-service': { x: 350, y: 260 },
  'notification-service': { x: 600, y: 180 },
}

function ServiceNode({ data }: { data: any }) {
  const { label, status, cpu, failureProbability, isFailed, isAffected } = data

  const glowColor = isFailed ? '#ef4444' : isAffected ? '#f97316' : status === 'warning' ? '#fbbf24' : '#34d399'
  const bgColor = isFailed
    ? 'rgba(239,68,68,0.15)'
    : isAffected
    ? 'rgba(249,115,22,0.1)'
    : status === 'warning'
    ? 'rgba(251,191,36,0.08)'
    : 'rgba(52,211,153,0.06)'

  return (
    <motion.div
      animate={
        isFailed
          ? { scale: [1, 1.05, 0.95, 1.02, 1], boxShadow: [`0 0 20px ${glowColor}88`, `0 0 40px ${glowColor}`, `0 0 20px ${glowColor}88`] }
          : isAffected
          ? { scale: [1, 1.02, 1] }
          : {}
      }
      transition={{ duration: 0.8, repeat: isFailed || isAffected ? Infinity : 0, repeatDelay: 0.5 }}
      style={{
        background: bgColor,
        border: `1px solid ${glowColor}44`,
        boxShadow: `0 0 15px ${glowColor}33, inset 0 1px 0 ${glowColor}22`,
      }}
      className="rounded-xl px-4 py-3 min-w-[140px] backdrop-blur-sm relative overflow-hidden"
    >
      {/* Top glow line */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px]"
        style={{ background: `linear-gradient(90deg, transparent, ${glowColor}, transparent)` }}
      />

      {/* Pulse ring on fail */}
      {(isFailed || isAffected) && (
        <div
          className="absolute inset-0 rounded-xl border-2 animate-ping opacity-30"
          style={{ borderColor: glowColor }}
        />
      )}

      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-2 h-2 rounded-full"
          style={{
            background: glowColor,
            boxShadow: `0 0 6px ${glowColor}`,
            animation: isFailed ? 'pulse-red 1s infinite' : 'pulse-green 2s infinite',
          }}
        />
        <span className="text-[11px] font-mono font-bold text-white">{label}</span>
      </div>

      <div className="flex justify-between text-[10px] font-mono text-white/40">
        <span>CPU: <span style={{ color: cpu > 70 ? '#ef4444' : '#64748b' }}>{isFailed ? '98' : isAffected ? Math.min(99, cpu + 30) : cpu}%</span></span>
        <span>Risk: <span style={{ color: failureProbability > 50 ? '#ef4444' : '#64748b' }}>{isFailed ? 100 : isAffected ? 89 : failureProbability}%</span></span>
      </div>

      {isFailed && (
        <div className="mt-1.5 text-[9px] font-mono font-bold text-red-400 tracking-widest">
          ⚡ FAILED
        </div>
      )}
      {isAffected && !isFailed && (
        <div className="mt-1.5 text-[9px] font-mono font-bold text-orange-400 tracking-widest">
          🔴 CASCADING
        </div>
      )}
    </motion.div>
  )
}

const nodeTypes = { serviceNode: ServiceNode }

export function DependencyGraph({ services, failedService, affectedServices }: DependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const buildGraph = useCallback(() => {
    const newNodes: Node[] = services.map(s => ({
      id: s.id,
      type: 'serviceNode',
      position: NODE_POSITIONS[s.id] || { x: 0, y: 0 },
      data: {
        label: s.name.replace('-service', ''),
        status: s.status,
        cpu: s.cpu,
        failureProbability: s.failureProbability,
        isFailed: failedService === s.id,
        isAffected: affectedServices.includes(s.id),
      },
      draggable: true,
    }))

    const newEdges: Edge[] = []
    services.forEach(s => {
      s.dependencies.forEach(dep => {
        const isCritical = failedService === s.id || failedService === dep
        newEdges.push({
          id: `${s.id}-${dep}`,
          source: s.id,
          target: dep,
          animated: isCritical,
          style: {
            stroke: isCritical ? '#ef4444' : '#1e3a4a',
            strokeWidth: isCritical ? 3 : 1.5,
            opacity: isCritical ? 1 : 0.5,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isCritical ? '#ef4444' : '#1e3a4a',
          },
        })
      })
    })

    setNodes(newNodes)
    setEdges(newEdges)
  }, [services, failedService, affectedServices, setNodes, setEdges])

  useEffect(() => {
    buildGraph()
  }, [buildGraph])

  return (
    <div className="relative w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.5}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#0d1929" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-3 text-[10px] font-mono text-white/40">
        <LegendItem color="#34d399" label="Healthy" />
        <LegendItem color="#fbbf24" label="Warning" />
        <LegendItem color="#ef4444" label="Critical/Failed" />
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full" style={{ background: color }} />
      <span>{label}</span>
    </div>
  )
}
