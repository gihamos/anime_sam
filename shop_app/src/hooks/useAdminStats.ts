import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DashboardStats } from '@/api/types'

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardStats>('/admin/api/stats')
      return data
    },
  })
}
