import { type PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

export function Card({
  children,
  className,
}: PropsWithChildren<{
  className?: string
}>) {
  return (
    <div className={cn('rounded-xl border border-border bg-surface p-4 shadow-soft', className)}>
      {children}
    </div>
  )
}

