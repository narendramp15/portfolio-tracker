import { type ReactNode } from 'react'

import { cn } from '../../lib/cn'
import { Card } from './Card'

export function KpiCard({
  label,
  value,
  helper,
  icon,
  tone = 'neutral',
}: {
  label: string
  value: string
  helper?: string
  icon?: ReactNode
  tone?: 'neutral' | 'success' | 'danger'
}) {
  const toneConfig = {
    neutral: { bg: 'bg-gradient-to-br from-indigo-600/10 to-purple-600/5', text: 'text-indigo-400', border: 'border-indigo-500/20', iconBg: 'bg-indigo-500/10' },
    success: { bg: 'bg-gradient-to-br from-emerald-600/10 to-teal-600/5', text: 'text-emerald-400', border: 'border-emerald-500/20', iconBg: 'bg-emerald-500/10' },
    danger: { bg: 'bg-gradient-to-br from-rose-600/10 to-red-600/5', text: 'text-rose-400', border: 'border-rose-500/20', iconBg: 'bg-rose-500/10' },
  }

  const config = toneConfig[tone]

  return (
    <Card className={cn('flex flex-col justify-between gap-4 min-h-[140px] border-zinc-800/60 hover:border-zinc-700/80 transition-all duration-300 group', config.bg, config.border)}>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-400 group-hover:text-zinc-300 transition-colors">{label}</div>
        <div className="mt-3 text-3xl font-black tracking-tight text-white group-hover:scale-105 transition-transform origin-left">{value}</div>
        {helper ? <div className={cn('mt-2 text-sm font-bold', config.text)}>{helper}</div> : null}
      </div>
      {icon ? (
        <div className={cn('self-end rounded-xl border p-3 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3', config.iconBg, config.border, config.text)}>
          {icon}
        </div>
      ) : null}
    </Card>
  )
}

