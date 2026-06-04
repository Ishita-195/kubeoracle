import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Sparkles, ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '../lib/utils'
import type { AIInsight } from '../types'

interface AIInsightPanelProps {
  insights: AIInsight[]
  isLoading: boolean
  simulationActive: boolean
  failedService: string | null
}

const SEVERITY_COLORS = {
  info: { text: '#06b6d4', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.15)' },
  warning: { text: '#fbbf24', bg: 'rgba(251,191,36,0.08)', border: 'rgba(251,191,36,0.15)' },
  critical: { text: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)' },
}

export function AIInsightPanel({ insights, isLoading, simulationActive, failedService }: AIInsightPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="relative">
          <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
            <Brain className="w-4 h-4 text-purple-400" />
          </div>
          {(isLoading || simulationActive) && (
            <div className="absolute inset-0 rounded-lg border border-purple-500/50 animate-ping opacity-50" />
          )}
        </div>
        <div>
          <h3 className="text-[11px] font-mono font-bold text-white tracking-wider uppercase">AI Remediation</h3>
          <p className="text-[9px] text-white/30 font-mono">Powered by Claude</p>
        </div>
        {isLoading && (
          <Loader2 className="w-3 h-3 text-purple-400 animate-spin ml-auto" />
        )}
        {simulationActive && !isLoading && (
          <motion.div
            className="ml-auto flex items-center gap-1 text-[9px] font-mono text-purple-400"
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <Sparkles className="w-3 h-3" />
            Analyzing...
          </motion.div>
        )}
      </div>

      {/* Insights list */}
      <div className="flex flex-col gap-2 overflow-y-auto flex-1">
        <AnimatePresence mode="popLayout">
          {insights.map((insight, idx) => {
            const colors = SEVERITY_COLORS[insight.severity]
            const isOpen = expanded === insight.id

            return (
              <motion.div
                key={insight.id}
                layout
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: idx * 0.1 }}
                style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
                className="rounded-lg overflow-hidden cursor-pointer"
                onClick={() => setExpanded(isOpen ? null : insight.id)}
              >
                <div className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className="text-[8px] font-mono font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
                          style={{ background: `${colors.text}22`, color: colors.text }}
                        >
                          {insight.severity}
                        </span>
                        <span className="text-[9px] font-mono text-white/30">
                          {insight.confidence}% confidence
                        </span>
                      </div>
                      <p className="text-[11px] font-mono font-bold text-white leading-snug">{insight.title}</p>
                    </div>
                    <ChevronRight
                      className="w-3 h-3 text-white/30 flex-shrink-0 mt-0.5 transition-transform"
                      style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
                    />
                  </div>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <p className="text-[10px] text-white/50 mt-2 leading-relaxed">{insight.description}</p>
                        <div
                          className="mt-2 p-2 rounded text-[10px] font-mono leading-relaxed"
                          style={{ background: 'rgba(0,0,0,0.3)', color: colors.text, border: `1px solid ${colors.border}` }}
                        >
                          <span className="text-white/30">$ </span>
                          {insight.action}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
