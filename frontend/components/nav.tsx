'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Gauge, Activity, Droplets, TrendingUp, Waves } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWSStore } from '@/hooks/useSensorWebSocket'

const LINKS = [
  { href: '/dashboard', label: 'Dashboard', icon: Gauge },
  { href: '/sensors', label: 'Sensor', icon: Activity },
  { href: '/valves', label: 'Katup', icon: Droplets },
  { href: '/predictions', label: 'Prediksi', icon: TrendingUp },
]

export default function Nav() {
  const pathname = usePathname()
  const { status } = useWSStore()
  const statusColor =
    status === 'connected'
      ? 'bg-emerald-500'
      : status === 'connecting'
        ? 'bg-amber-400 animate-pulse'
        : 'bg-rose-500'
  const statusLabel =
    status === 'connected' ? 'Live' : status === 'connecting' ? 'Menghubungkan' : 'Terputus'

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur-md">
        <div className="container mx-auto max-w-7xl px-4 flex h-14 items-center gap-8">
          <Link href="/dashboard" className="flex items-center gap-2 shrink-0 group">
            <Waves className="w-4 h-4 text-primary transition-transform duration-200 group-hover:scale-110" strokeWidth={2} />
            <span className="font-semibold text-sm tracking-tight text-foreground">
              Aminuddin<span className="text-primary">.</span>
            </span>
          </Link>

          <nav className="hidden md:flex gap-0.5 flex-1">
            {LINKS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors duration-150',
                  pathname.startsWith(href)
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary',
                )}
              >
                <Icon className="w-3.5 h-3.5" strokeWidth={pathname.startsWith(href) ? 2 : 1.5} />
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-1.5 shrink-0 ml-auto md:ml-0">
            <span className={cn('w-1.5 h-1.5 rounded-full', statusColor)} />
            <span className="text-xs text-muted-foreground">{statusLabel}</span>
          </div>
        </div>
      </header>

      {/* Bottom tab bar — mobile only */}
      <nav
        aria-label="Navigasi utama"
        className="fixed bottom-0 inset-x-0 z-40 md:hidden border-t border-border/60 bg-background/95 backdrop-blur-md"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="grid grid-cols-4 h-16">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex flex-col items-center justify-center gap-1 text-[0.68rem] font-medium transition-colors duration-150',
                  active ? 'text-primary' : 'text-muted-foreground active:text-foreground',
                )}
              >
                <Icon className="w-5 h-5" strokeWidth={active ? 2 : 1.5} />
                {label}
              </Link>
            )
          })}
        </div>
      </nav>
    </>
  )
}
