import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DlQuota, DownloadRecord } from '@/api/types'

const DOWNLOADS_KEY = ['admin-downloads']
const QUOTAS_KEY = ['dl-quotas']

export function useDownloadHistory() {
  return useQuery({
    queryKey: DOWNLOADS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<DownloadRecord[]>('/admin/api/downloads')
      return data
    },
  })
}

export function useClearDownloadHistory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete('/admin/api/downloads')
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: DOWNLOADS_KEY }),
  })
}

export function useDlQuotas() {
  return useQuery({
    queryKey: QUOTAS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<DlQuota[]>('/admin/api/dl-quotas')
      return data
    },
  })
}

export function useSetDlQuota() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      username,
      maxFilesPerDay,
      maxGbPerDay,
      canDownload,
    }: {
      username: string
      maxFilesPerDay: number
      maxGbPerDay: number
      canDownload: boolean
    }) => {
      const { data } = await apiClient.put<DlQuota>(`/admin/api/dl-quotas/${encodeURIComponent(username)}`, {
        max_files_per_day: maxFilesPerDay,
        max_gb_per_day: maxGbPerDay,
        can_download: canDownload,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUOTAS_KEY }),
  })
}

export function useDeleteDlQuota() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (username: string) => {
      await apiClient.delete(`/admin/api/dl-quotas/${encodeURIComponent(username)}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUOTAS_KEY }),
  })
}
