import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Ticket } from '@/api/types'

const TICKETS_KEY = ['tickets']

export function useMyTickets() {
  return useQuery({
    queryKey: TICKETS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<Ticket[]>('/tickets')
      return data
    },
  })
}

export function useTicket(ticketId: string | null) {
  return useQuery({
    queryKey: [...TICKETS_KEY, ticketId],
    queryFn: async () => {
      const { data } = await apiClient.get<Ticket>(`/tickets/${ticketId}`)
      return data
    },
    enabled: !!ticketId,
    refetchInterval: 15_000,
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ subject, message }: { subject: string; message: string }) => {
      const { data } = await apiClient.post<Ticket>('/tickets', { subject, message })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TICKETS_KEY }),
  })
}

export function useReplyToTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticketId, body }: { ticketId: string; body: string }) => {
      const { data } = await apiClient.post<Ticket>(`/tickets/${ticketId}/messages`, { body })
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: [...TICKETS_KEY, vars.ticketId] })
      queryClient.invalidateQueries({ queryKey: TICKETS_KEY })
    },
  })
}
