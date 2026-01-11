import { type PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

export function Card({
  children,
  className,
  variant = 'default',
}: PropsWithChildren<{
  className?: string
  variant?: 'default' | 'glass' | 'gradient'
}>) {
  const variants = {
    default: 'rounded-2xl border border-border bg-surface shadow-xl hover:shadow-2xl hover:border-border/80 transition-all duration-300',
    glass: 'rounded-2xl border border-border/50 bg-surface/40 backdrop-blur-xl shadow-xl hover:border-border/70 transition-all duration-300',
    gradient: 'rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-900/40 via-purple-900/20 to-indigo-800/30 dark:from-indigo-900/40 dark:via-purple-900/20 dark:to-zinc-900/40 shadow-2xl shadow-indigo-500/10 hover:shadow-indigo-500/20 backdrop-blur-sm transition-all duration-300',
  }

  return (
    <div className={cn(variants[variant], 'p-6', className)}>
      {children}
    </div>
  )
}

