import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Ticket, TicketStatus } from '@/api/types'

const TICKETS_KEY = ['admin', 'tickets']

export function useAdminTickets(status?: TicketStatus) {
  return useQuery({
    queryKey: [...TICKETS_KEY, status ?? 'all'],
    queryFn: async () => {
      const { data } = await apiClient.get<Ticket[]>('/admin/api/tickets', { params: status ? { status } : {} })
      return data
    },
  })
}

export function useAdminTicket(ticketId: string | null) {
  return useQuery({
    queryKey: [...TICKETS_KEY, 'detail', ticketId],
    queryFn: async () => {
      const { data } = await apiClient.get<Ticket>(`/admin/api/tickets/${ticketId}`)
      return data
    },
    enabled: !!ticketId,
  })
}

export function useAdminReplyToTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticketId, body }: { ticketId: string; body: string }) => {
      const { data } = await apiClient.post<Ticket>(`/admin/api/tickets/${ticketId}/messages`, { body })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TICKETS_KEY }),
  })
}

export function useUpdateTicketStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticketId, status }: { ticketId: string; status: TicketStatus }) => {
      const { data } = await apiClient.put<Ticket>(`/admin/api/tickets/${ticketId}/status`, { status })
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TICKETS_KEY }),
  })
}
