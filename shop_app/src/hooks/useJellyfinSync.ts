import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

const SYNC_STATUS_KEY = ['admin', 'jellyfin-sync-status']

export interface JellyfinSyncStatus {
  last_sync: string | null
  reachable: boolean
}

export function useJellyfinSyncStatus() {
  return useQuery({
    queryKey: SYNC_STATUS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<JellyfinSyncStatus>('/admin/api/jellyfin/sync-status')
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SYNC_STATUS_KEY }),
  })
}

const AUTO_SYNC_KEY = ['admin', 'jellyfin-auto-sync']

export interface JellyfinAutoSyncConfig {
  enabled: boolean
  interval_hours: number
}

export function useJellyfinAutoSync() {
  return useQuery({
    queryKey: AUTO_SYNC_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<JellyfinAutoSyncConfig>('/admin/api/jellyfin/auto-sync')
      return data
    },
  })
}

export function useUpdateJellyfinAutoSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (config: JellyfinAutoSyncConfig) => {
      const { data } = await apiClient.put<JellyfinAutoSyncConfig>('/admin/api/jellyfin/auto-sync', config)
      return data
    },
    onSuccess: (data) => queryClient.setQueryData(AUTO_SYNC_KEY, data),
  })
}
