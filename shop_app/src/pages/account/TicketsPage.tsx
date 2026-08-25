import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2, Plus } from 'lucide-react'
import { useMyTickets, useCreateTicket } from '@/hooks/useTickets'
import { getApiError } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'

const STATUS_VARIANT: Record<string, 'default' | 'secondary'> = {
  open: 'default',
  pending: 'secondary',
  closed: 'secondary',
}

const STATUS_LABEL: Record<string, string> = {
  open: 'Ouvert',
  pending: 'En attente',
  closed: 'Clos',
}

export function TicketsPage() {
  const { data: tickets, isLoading } = useMyTickets()
  const createTicket = useCreateTicket()
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')

  async function handleCreate() {
    if (!subject.trim() || !message.trim()) return
    try {
      await createTicket.mutateAsync({ subject, message })
      setSubject('')
      setMessage('')
      setOpen(false)
      toast.success('Ticket créé')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Support</h1>
          <p className="text-sm text-muted-foreground">Contactez-nous en cas de problème avec votre accès.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button size="sm" className="gap-2" />}>
            <Plus className="size-4" />
            Nouveau ticket
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nouveau ticket</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="subject">Sujet</Label>
                <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} autoFocus />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="message">Message</Label>
                <Textarea id="message" rows={5} value={message} onChange={(e) => setMessage(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Annuler</Button>
              <Button onClick={handleCreate} disabled={createTicket.isPending}>
                {createTicket.isPending && <Loader2 className="size-4 animate-spin" />}
                Envoyer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <Skeleton className="h-40 rounded-lg" />}

      {!isLoading && (!tickets || tickets.length === 0) && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Aucun ticket pour le moment.
          </CardContent>
        </Card>
      )}

      {!isLoading && tickets && tickets.length > 0 && (
        <div className="space-y-2">
          {tickets.map((t) => (
            <Link key={t.id} to={`/compte/tickets/${t.id}`}>
              <Card className="transition-colors hover:bg-accent/50">
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="text-sm font-medium">{t.subject}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(t.updated_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANT[t.status] ?? 'secondary'}>{STATUS_LABEL[t.status] ?? t.status}</Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
