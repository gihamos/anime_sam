import { useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Ticket } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'

interface TicketThreadProps {
  ticket: Ticket
  viewerRole: 'customer' | 'admin'
  canReply: boolean
  onReply: (body: string) => Promise<void>
  isReplying: boolean
}

export function TicketThread({ ticket, viewerRole, canReply, onReply, isReplying }: TicketThreadProps) {
  const [body, setBody] = useState('')

  async function handleSend() {
    if (!body.trim()) return
    await onReply(body)
    setBody('')
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {ticket.messages.map((m, i) => {
          const isOwn = m.author_role === viewerRole
          return (
            <div key={i} className={cn('flex', isOwn ? 'justify-end' : 'justify-start')}>
              <div
                className={cn(
                  'max-w-[80%] rounded-lg border border-border px-3 py-2 text-sm',
                  isOwn ? 'bg-primary/10' : 'bg-card',
                )}
              >
                <p className="mb-1 text-xs font-medium text-muted-foreground">
                  {m.author_role === 'admin' ? 'Support' : m.author_username}
                </p>
                <p className="whitespace-pre-wrap">{m.body}</p>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {new Date(m.created_at).toLocaleString('fr-FR')}
                </p>
              </div>
            </div>
          )
        })}
      </div>

      {canReply ? (
        <Card>
          <CardContent className="space-y-2 p-3">
            <Textarea
              rows={3}
              placeholder="Votre réponse..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <div className="flex justify-end">
              <Button size="sm" onClick={handleSend} disabled={isReplying || !body.trim()}>
                {isReplying ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                Envoyer
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <p className="text-center text-xs text-muted-foreground">Ce ticket est clos.</p>
      )}
    </div>
  )
}
