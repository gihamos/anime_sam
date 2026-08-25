import { useState } from 'react'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import {
  useAdminTickets, useAdminTicket, useAdminReplyToTicket, useUpdateTicketStatus,
} from '@/hooks/useAdminTickets'
import { getApiError } from '@/api/client'
import type { TicketStatus } from '@/api/types'
import { TicketThread } from '@/components/shared/TicketThread'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const STATUS_OPTIONS: { value: TicketStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tous statuts' },
  { value: 'open', label: 'Ouverts' },
  { value: 'pending', label: 'En attente' },
  { value: 'closed', label: 'Clos' },
]

export function TicketsAdminPage() {
  const [statusFilter, setStatusFilter] = useState<TicketStatus | 'all'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: tickets = [], isLoading } = useAdminTickets(statusFilter === 'all' ? undefined : statusFilter)
  const { data: ticket } = useAdminTicket(selectedId)
  const reply = useAdminReplyToTicket()
  const updateStatus = useUpdateTicketStatus()

  async function handleReply(body: string) {
    if (!selectedId) return
    try {
      await reply.mutateAsync({ ticketId: selectedId, body })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleStatusChange(status: TicketStatus) {
    if (!selectedId) return
    try {
      await updateStatus.mutateAsync({ ticketId: selectedId, status })
      toast.success('Statut mis à jour')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  if (selectedId && ticket) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" onClick={() => setSelectedId(null)}>
            <ArrowLeft className="size-4" />
            Retour
          </Button>
          <Select value={ticket.status} onValueChange={(v) => handleStatusChange(v as TicketStatus)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">Ouvert</SelectItem>
              <SelectItem value="pending">En attente</SelectItem>
              <SelectItem value="closed">Clos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <h1 className="text-xl font-semibold">{ticket.subject}</h1>
          <p className="text-sm text-muted-foreground">Client : {ticket.username}</p>
        </div>
        <TicketThread
          ticket={ticket}
          viewerRole="admin"
          canReply={ticket.status !== 'closed'}
          onReply={handleReply}
          isReplying={reply.isPending}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Tickets</h1>
          <p className="text-sm text-muted-foreground">Boîte de réception du support client.</p>
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as TicketStatus | 'all')}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <Skeleton className="h-40 rounded-lg" />}

      {!isLoading && tickets.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">Aucun ticket.</CardContent>
        </Card>
      )}

      {!isLoading && tickets.length > 0 && (
        <div className="space-y-2">
          {tickets.map((t) => (
            <Card key={t.id} className="cursor-pointer transition-colors hover:bg-accent/50" onClick={() => setSelectedId(t.id)}>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium">{t.subject}</p>
                  <p className="text-xs text-muted-foreground">{t.username} — {new Date(t.updated_at).toLocaleDateString('fr-FR')}</p>
                </div>
                <Badge variant={t.status === 'closed' ? 'secondary' : 'default'}>{t.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
