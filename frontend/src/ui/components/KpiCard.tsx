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
  const helperClass =
    tone === 'success'
      ? 'text-success'
      : tone === 'danger'
        ? 'text-danger'
        : 'text-muted'

  return (
    <Card className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
        <div className="mt-2 text-2xl font-semibold tracking-tight">{value}</div>
        {helper ? <div className={cn('mt-1 text-sm', helperClass)}>{helper}</div> : null}
      </div>
      {icon ? <div className="rounded-xl border border-border bg-bg p-2 text-muted">{icon}</div> : null}
    </Card>
  )
}

