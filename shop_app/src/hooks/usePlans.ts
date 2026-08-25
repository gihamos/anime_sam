import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Plan } from '@/api/types'

export function usePlans() {
  return useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const { data } = await apiClient.get<Plan[]>('/billing/plans')
      return data
    },
  })
}
