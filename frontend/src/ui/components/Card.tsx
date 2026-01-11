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
    default: 'rounded-2xl border border-zinc-800/60 bg-gradient-to-br from-zinc-900/90 via-slate-900/80 to-zinc-900/90 shadow-xl shadow-black/20 hover:shadow-2xl hover:shadow-indigo-500/5 hover:border-zinc-700/80 transition-all duration-300 backdrop-blur-sm',
    glass: 'rounded-2xl border border-zinc-800/50 bg-zinc-900/40 backdrop-blur-xl shadow-xl shadow-black/20 hover:shadow-2xl hover:border-zinc-700/70 transition-all duration-300',
    gradient: 'rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-900/40 via-purple-900/20 to-zinc-900/40 shadow-2xl shadow-indigo-500/10 hover:shadow-indigo-500/20 hover:from-indigo-900/50 hover:via-purple-900/30 backdrop-blur-sm transition-all duration-300',
  }

  return (
    <div className={cn(variants[variant], 'p-6', className)}>
      {children}
    </div>
  )
}

