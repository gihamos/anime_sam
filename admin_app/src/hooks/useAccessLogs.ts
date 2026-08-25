import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { AccessLogEntry, AccessStats } from '@/api/types'

export type ConnFilter = 'all' | 'auth' | 'anon'

export function useAccessLogs(filter: ConnFilter) {
  return useQuery({
    queryKey: ['access-logs', filter],
    queryFn: async () => {
      const { data } = await apiClient.get<AccessLogEntry[]>('/admin/api/access-logs', {
        params: {
          auth_only: filter === 'auth' || undefined,
          anon_only: filter === 'anon' || undefined,
        },
      })
      return data
    },
  })
}

export function useAccessStats() {
  return useQuery({
    queryKey: ['access-logs-stats'],
    queryFn: async () => {
      const { data } = await apiClient.get<AccessStats>('/admin/api/access-logs/stats')
      return data
    },
  })
}

export function useClearAccessLogs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete('/admin/api/access-logs')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-logs'] })
      queryClient.invalidateQueries({ queryKey: ['access-logs-stats'] })
    },
  })
}
