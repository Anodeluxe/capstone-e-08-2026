import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'
import Providers from '@/components/providers'
import Nav from '@/components/nav'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Toren Monitoring',
  description: 'Sistem Monitoring Kualitas Air Toren',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50">
        <Providers>
          <Nav />
          <main className="flex-1 container mx-auto max-w-7xl px-4 py-6">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  )
}
