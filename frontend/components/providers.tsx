'use client'

import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSensorWebSocket } from '@/hooks/useSensorWebSocket'

function WSInitializer() {
  useSensorWebSocket()
  return null
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 10_000, retry: 2 },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <WSInitializer />
      {children}
    </QueryClientProvider>
  )
}
