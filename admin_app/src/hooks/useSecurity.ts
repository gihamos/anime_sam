import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { IpBan, SecurityState } from '@/api/types'

const SECURITY_KEY = ['security-state']
const BANS_KEY = ['ip-bans']

export function useSecurityState() {
  return useQuery({
    queryKey: SECURITY_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<SecurityState>('/admin/api/security/state')
      return data
    },
  })
}

export function useSetApiLock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ locked, reason }: { locked: boolean; reason: string }) => {
      const { data } = await apiClient.put('/admin/api/security/lock', { locked, reason })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SECURITY_KEY }),
  })
}

export function useIpBans() {
  return useQuery({
    queryKey: BANS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<IpBan[]>('/admin/api/security/ip-bans')
      return data
    },
  })
}

export function useAddIpBan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ip, reason }: { ip: string; reason: string }) => {
      const { data } = await apiClient.post('/admin/api/security/ip-bans', { ip, reason })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BANS_KEY })
      queryClient.invalidateQueries({ queryKey: SECURITY_KEY })
    },
  })
}

export function useRemoveIpBan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (ip: string) => {
      await apiClient.delete(`/admin/api/security/ip-bans/${encodeURIComponent(ip)}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BANS_KEY })
      queryClient.invalidateQueries({ queryKey: SECURITY_KEY })
    },
  })
}
