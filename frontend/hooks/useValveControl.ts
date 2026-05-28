'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { valvesApi } from '@/lib/api'
import type { ValveID, ValveCommandPayload } from '@/types'

export function useValveCommand() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ valveId, payload }: { valveId: ValveID; payload: ValveCommandPayload }) =>
      valvesApi.command(valveId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['valves'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
    },
  })
}
