import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

const STATUS_KEY = ['jellyfin', 'sync-status']

export function useJellyfinSyncStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<{ last_sync: string | null }>('/admin/api/jellyfin/sync-status')
      return data
    },
  })
}

export function useTriggerJellyfinSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<{ ok: boolean }>('/admin/api/jellyfin/sync')
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: STATUS_KEY }),
  })
}
