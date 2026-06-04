import { motion, AnimatePresence } from 'framer-motion'
import { AlertOctagon, Zap } from 'lucide-react'
import type { SimulationState } from '../types'

interface SimulationBannerProps {
  simulation: SimulationState
  logs: string[]
}

const PHASE_LABELS: Record<string, string> = {
  idle: '',
  initiating: 'INITIATING FAILURE SIMULATION',
  propagating: 'PROPAGATING CASCADE',
  cascading: 'CASCADE BLAST RADIUS EXPANDING',
  recovering: 'KUBERNETES SELF-HEALING',
}

export function SimulationBanner({ simulation, logs }: SimulationBannerProps) {
  return (
    <AnimatePresence>
      {simulation.active && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="overflow-hidden"
        >
          <div className="glass-card-red rounded-xl p-4 mb-4 relative overflow-hidden border-glow-red">
            {/* Animated background */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <motion.div
                className="absolute inset-0"
                animate={{ backgroundPosition: ['0% 0%', '100% 100%'] }}
                transition={{ duration: 3, repeat: Infinity, repeatType: 'reverse' }}
                style={{
                  background: 'repeating-linear-gradient(45deg, transparent, transparent 20px, rgba(239,68,68,0.03) 20px, rgba(239,68,68,0.03) 40px)',
                }}
              />
            </div>

            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-3">
                <motion.div
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity }}
                >
                  <AlertOctagon className="w-5 h-5 text-red-400" />
                </motion.div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-display text-sm font-bold text-red-400 tracking-widest">
                      {PHASE_LABELS[simulation.phase]}
                    </span>
                    <motion.div
                      className="flex gap-1"
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 0.8, repeat: Infinity }}
                    >
                      {[0, 1, 2].map(i => (
                        <div key={i} className="w-1 h-1 rounded-full bg-red-400" />
                      ))}
                    </motion.div>
                  </div>
                  <p className="text-[11px] text-white/40 font-mono mt-0.5">
                    Failed: <span className="text-red-300">{simulation.failedService}</span>
                    {simulation.affectedServices.length > 0 && (
                      <> · Blast radius: <span className="text-orange-300">{simulation.affectedServices.join(', ')}</span></>
                    )}
                  </p>
                </div>

                {/* Progress */}
                <div className="ml-auto flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-[9px] font-mono text-white/30 mb-1">SIMULATION PROGRESS</div>
                    <div className="font-display text-lg font-bold text-red-400">{simulation.progress}%</div>
                  </div>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-1 bg-white/10 rounded-full overflow-hidden mb-3">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-red-600 to-red-400"
                  animate={{ width: `${simulation.progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>

              {/* Log feed */}
              <div className="font-mono text-[10px] space-y-1 max-h-20 overflow-y-auto">
                {logs.slice(-5).map((log, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-white/60"
                  >
                    <span className="text-white/20 mr-2">[{new Date().toLocaleTimeString()}]</span>
                    {log}
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
