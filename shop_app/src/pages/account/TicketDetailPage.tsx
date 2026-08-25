import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { toast } from 'sonner'
import { useTicket, useReplyToTicket } from '@/hooks/useTickets'
import { getApiError } from '@/api/client'
import { TicketThread } from '@/components/shared/TicketThread'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const { data: ticket, isLoading } = useTicket(ticketId ?? null)
  const reply = useReplyToTicket()

  async function handleReply(body: string) {
    if (!ticketId) return
    try {
      await reply.mutateAsync({ ticketId, body })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  if (isLoading) return <Skeleton className="h-64 rounded-lg" />
  if (!ticket) return <p className="text-sm text-muted-foreground">Ticket introuvable.</p>

  return (
    <div className="space-y-6">
      <div>
        <Button
          variant="ghost"
          size="sm"
          className="mb-2 gap-1.5 text-muted-foreground"
          render={<Link to="/compte/tickets" />}
          nativeButton={false}
        >
          <ArrowLeft className="size-4" />
          Retour
        </Button>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">{ticket.subject}</h1>
          <Badge variant="secondary">{ticket.status}</Badge>
        </div>
      </div>

      <TicketThread
        ticket={ticket}
        viewerRole="customer"
        canReply={ticket.status !== 'closed'}
        onReply={handleReply}
        isReplying={reply.isPending}
      />
    </div>
  )
}
