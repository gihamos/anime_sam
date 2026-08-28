import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Payment, PromoPreview, SubscriptionDetail } from '@/api/types'

const SUBSCRIPTION_KEY = ['me', 'subscription']
const PAYMENTS_KEY = ['me', 'payments']

export function useMySubscription() {
  return useQuery({
    queryKey: SUBSCRIPTION_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionDetail | null>('/billing/me/subscription')
      return data
    },
  })
}

export function useMyPayments() {
  return useQuery({
    queryKey: PAYMENTS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Payment[]>('/billing/me/payments')
      return data
    },
  })
}

export function useSubscribe() {
  return useMutation({
    mutationFn: async ({
      planId, autoRenew, promoCode,
    }: { planId: string; autoRenew: boolean; promoCode?: string }) => {
      const { data } = await apiClient.post<{ subscription_id: string; approval_url: string }>(
        '/billing/subscribe',
        { plan_id: planId, auto_renew: autoRenew, promo_code: promoCode || null },
      )
      return data
    },
  })
}

export function usePromoPreview(code: string, planId: string | null) {
  return useQuery({
    queryKey: ['promo-preview', code, planId],
    queryFn: async () => {
      const { data } = await apiClient.get<PromoPreview>(
        `/billing/promo/${encodeURIComponent(code)}?plan_id=${encodeURIComponent(planId as string)}`,
      )
      return data
    },
    enabled: !!code && !!planId,
    retry: false,
  })
}

export function useConfirmSubscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (subscriptionId: string) => {
      const { data } = await apiClient.post<SubscriptionDetail>(
        `/billing/subscribe/confirm?subscription_id=${encodeURIComponent(subscriptionId)}`,
      )
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUBSCRIPTION_KEY }),
  })
}

export function useCancelSubscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (reason?: string) => {
      const { data } = await apiClient.post('/billing/me/subscription/cancel', { reason: reason || null })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUBSCRIPTION_KEY }),
  })
}

export function useChangePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (newPlanId: string) => {
      const { data } = await apiClient.post('/billing/me/subscription/change-plan', { new_plan_id: newPlanId })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUBSCRIPTION_KEY }),
  })
}
