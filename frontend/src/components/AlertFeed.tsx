import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, Info, XCircle, X } from 'lucide-react'
import { cn } from '../lib/utils'
import type { Alert } from '../types'

interface AlertFeedProps {
  alerts: Alert[]
  onDismiss: (id: string) => void
}

const SEVERITY_CONFIG = {
  info: { color: '#06b6d4', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.2)', icon: Info, label: 'INFO' },
  warning: { color: '#fbbf24', bg: 'rgba(251,191,36,0.08)', border: 'rgba(251,191,36,0.2)', icon: AlertTriangle, label: 'WARN' },
  critical: { color: '#ef4444', bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', icon: XCircle, label: 'CRIT' },
}

export function AlertFeed({ alerts, onDismiss }: AlertFeedProps) {
  const active = alerts.filter(a => !a.acknowledged)

  return (
    <div className="flex flex-col gap-2">
      <AnimatePresence mode="popLayout">
        {active.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-6 text-white/20 text-xs font-mono"
          >
            ✓ No active alerts
          </motion.div>
        ) : (
          active.map(alert => {
            const config = SEVERITY_CONFIG[alert.severity]
            const Icon = config.icon
            const time = new Date(alert.timestamp).toLocaleTimeString()

            return (
              <motion.div
                key={alert.id}
                layout
                initial={{ opacity: 0, x: 40, height: 0 }}
                animate={{ opacity: 1, x: 0, height: 'auto' }}
                exit={{ opacity: 0, x: 40, height: 0 }}
                transition={{ duration: 0.3 }}
                className={cn(
                  'relative rounded-lg p-3 text-xs overflow-hidden',
                  alert.severity === 'critical' && 'border-glow-red',
                )}
                style={{ background: config.bg, border: `1px solid ${config.border}` }}
              >
                <div className="flex items-start gap-2">
                  <Icon className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: config.color }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
                        style={{ background: `${config.color}22`, color: config.color }}
                      >
                        {config.label}
                      </span>
                      <span className="font-mono font-bold text-white/80 text-[11px]">{alert.service}</span>
                      <span className="text-white/20 font-mono text-[9px] ml-auto">{time}</span>
                    </div>
                    <p className="text-white/60 leading-relaxed">{alert.message}</p>
                  </div>
                  <button
                    onClick={() => onDismiss(alert.id)}
                    className="flex-shrink-0 text-white/20 hover:text-white/60 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            )
          })
        )}
      </AnimatePresence>
    </div>
  )
}
