import { Dashboard } from './pages/Dashboard'
import { MLOpsDashboard } from './pages/MLOpsDashboard'
import { useState } from 'react'
import { Activity, BarChart2 } from 'lucide-react'

const TABS = [
  { id: 'observability', label: 'Observability', icon: Activity },
  { id: 'mlops', label: 'MLOps', icon: BarChart2 },
]

export default function App() {
  const [tab, setTab] = useState('observability')

  return (
    <div className="min-h-screen flex flex-col overflow-hidden">

      {/* Tab bar — sits below the main Header when on observability page */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-white/5 bg-black/20 backdrop-blur-sm sticky top-0 z-40">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold uppercase tracking-widest transition-all ${
              tab === id
                ? 'bg-cyan-500/15 border border-cyan-500/30 text-cyan-400'
                : 'text-white/30 hover:text-white/60 hover:bg-white/4'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'observability' ? <Dashboard /> : <MLOpsDashboard />}
    </div>
  )
}
