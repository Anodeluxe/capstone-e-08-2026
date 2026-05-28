'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, Gauge, Droplets, TrendingUp } from 'lucide-react'
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

  return (
    <header className="sticky top-0 z-40 border-b bg-white dark:bg-zinc-900 shadow-sm">
      <div className="container mx-auto max-w-7xl px-4 flex h-14 items-center gap-6">
        <span className="font-semibold text-sm shrink-0 text-zinc-800 dark:text-zinc-100">
          Toren Monitoring
        </span>
        <nav className="flex gap-1 flex-1">
          {LINKS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
                pathname.startsWith(href)
                  ? 'bg-zinc-100 dark:bg-zinc-800 font-medium text-zinc-900 dark:text-zinc-50'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-800',
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 shrink-0">
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              status === 'connected'
                ? 'bg-green-500'
                : status === 'connecting'
                  ? 'bg-yellow-400 animate-pulse'
                  : 'bg-red-500',
            )}
          />
          {status === 'connected'
            ? 'Live'
            : status === 'connecting'
              ? 'Menghubungkan...'
              : 'Terputus'}
        </div>
      </div>
    </header>
  )
}
