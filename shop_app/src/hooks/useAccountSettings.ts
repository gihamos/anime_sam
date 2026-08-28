import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { Customer } from '@/api/types'

export function useUpdateAccount() {
  return useMutation({
    mutationFn: async ({ email, dateOfBirth }: { email: string; dateOfBirth?: string }) => {
      const { data } = await apiClient.put<Customer>('/auth/me', {
        email: email || null,
        date_of_birth: dateOfBirth || null,
      })
      return data
    },
    onSuccess: (data) => useAuthStore.setState({ customer: data }),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) => {
      const { data } = await apiClient.put<{ message: string }>('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      return data
    },
  })
}
