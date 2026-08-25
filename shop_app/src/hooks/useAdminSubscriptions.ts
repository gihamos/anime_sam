import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Payment, SubscriptionAdmin } from '@/api/types'

const SUBS_KEY = ['admin', 'subscriptions']

export function useAdminSubscriptions(filters: { status?: string; plan_id?: string; search?: string }) {
  return useQuery({
    queryKey: [...SUBS_KEY, filters],
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionAdmin[]>('/admin/api/subscriptions', { params: filters })
      return data
    },
  })
}

export function useAdminSubscriptionDetail(id: string | null) {
  return useQuery({
    queryKey: [...SUBS_KEY, id],
    queryFn: async () => {
      const { data } = await apiClient.get<{ subscription: SubscriptionAdmin; payments: Payment[] }>(
        `/admin/api/subscriptions/${id}`,
      )
      return data
    },
    enabled: !!id,
  })
}

export function useExtendSubscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, days }: { id: string; days: number }) => {
      const { data } = await apiClient.post<SubscriptionAdmin>(`/admin/api/subscriptions/${id}/extend`, { days })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUBS_KEY }),
  })
}

export function useForceCancelSubscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason?: string }) => {
      const { data } = await apiClient.post<SubscriptionAdmin>(`/admin/api/subscriptions/${id}/cancel`, {
        reason: reason || null,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUBS_KEY }),
  })
}
