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
    neutral: {
      bg: 'bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-600/10 dark:to-purple-600/5',
      text: 'text-indigo-600 dark:text-indigo-400',
      border: 'border-indigo-200 dark:border-indigo-500/20',
      iconBg: 'bg-indigo-100 dark:bg-indigo-500/10',
      labelText: 'text-indigo-800/70 dark:text-zinc-400',
      valueText: 'text-indigo-900 dark:text-white'
    },
    success: {
      bg: 'bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-600/10 dark:to-teal-600/5',
      text: 'text-emerald-600 dark:text-emerald-400',
      border: 'border-emerald-200 dark:border-emerald-500/20',
      iconBg: 'bg-emerald-100 dark:bg-emerald-500/10',
      labelText: 'text-emerald-800/70 dark:text-zinc-400',
      valueText: 'text-emerald-900 dark:text-white'
    },
    danger: {
      bg: 'bg-gradient-to-br from-rose-50 to-red-50 dark:from-rose-600/10 dark:to-red-600/5',
      text: 'text-rose-600 dark:text-rose-400',
      border: 'border-rose-200 dark:border-rose-500/20',
      iconBg: 'bg-rose-100 dark:bg-rose-500/10',
      labelText: 'text-rose-800/70 dark:text-zinc-400',
      valueText: 'text-rose-900 dark:text-white'
    },
  }

  const config = toneConfig[tone]

  return (
    <Card className={cn('flex flex-col justify-between gap-4 min-h-[140px] hover:border-opacity-80 transition-all duration-300 group', config.bg, config.border)}>
      <div className="min-w-0 flex-1">
        <div className={cn('text-xs font-bold uppercase tracking-widest transition-colors', config.labelText)}>{label}</div>
        <div className={cn('mt-3 text-3xl font-black tracking-tight group-hover:scale-105 transition-transform origin-left', config.valueText)}>{value}</div>
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

