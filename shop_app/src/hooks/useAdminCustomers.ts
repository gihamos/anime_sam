import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Customer } from '@/api/types'

const CUSTOMERS_KEY = ['admin', 'customers']

export function useAdminCustomers() {
  return useQuery({
    queryKey: CUSTOMERS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Customer[]>('/admin/api/customers')
      return data
    },
  })
}

export interface CreatedCustomer {
  username: string
  email: string | null
  generated_password: string | null
}

export function useCreateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (
      { username, email, password, dateOfBirth }: { username: string; email?: string; password?: string; dateOfBirth: string },
    ) => {
      const { data } = await apiClient.post<CreatedCustomer>('/admin/api/customers', {
        username,
        email: email || null,
        password: password || null,
        date_of_birth: dateOfBirth,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CUSTOMERS_KEY }),
  })
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (
      { username, email, newPassword, dateOfBirth }: { username: string; email?: string; newPassword?: string; dateOfBirth?: string },
    ) => {
      const { data } = await apiClient.put<Customer>(`/admin/api/customers/${encodeURIComponent(username)}`, {
        email: email || null,
        new_password: newPassword || null,
        date_of_birth: dateOfBirth || null,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CUSTOMERS_KEY }),
  })
}

export function useDeleteCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (username: string) => {
      await apiClient.delete(`/admin/api/customers/${encodeURIComponent(username)}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CUSTOMERS_KEY }),
  })
}

export function useUpdateCustomerStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ username, isActive }: { username: string; isActive: boolean }) => {
      const { data } = await apiClient.put<Customer>(`/admin/api/customers/${encodeURIComponent(username)}/status`, {
        is_active: isActive,
      })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CUSTOMERS_KEY }),
  })
}
