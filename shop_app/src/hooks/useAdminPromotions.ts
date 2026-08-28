import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { DiscountType, Promotion } from '@/api/types'

const PROMOTIONS_KEY = ['admin', 'promotions']

export interface PromotionFormValues {
  code: string
  description: string
  discount_type: DiscountType
  discount_value: number
  applicable_plan_ids: string[]
  max_uses: number | null
  expires_at: string | null
  is_active: boolean
}

export function useAdminPromotions() {
  return useQuery({
    queryKey: PROMOTIONS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Promotion[]>('/admin/api/promotions')
      return data
    },
  })
}

export function useCreatePromotion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: PromotionFormValues) => {
      const { data } = await apiClient.post<Promotion>('/admin/api/promotions', body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROMOTIONS_KEY }),
  })
}

export function useUpdatePromotion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: Partial<PromotionFormValues> }) => {
      const { data } = await apiClient.put<Promotion>(`/admin/api/promotions/${id}`, body)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROMOTIONS_KEY }),
  })
}

export function useDeletePromotion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/admin/api/promotions/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROMOTIONS_KEY }),
  })
}
