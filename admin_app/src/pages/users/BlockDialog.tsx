import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useUpdateUser } from '@/hooks/useUsers'
import type { User } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface BlockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
}

export function BlockDialog({ open, onOpenChange, user }: BlockDialogProps) {
  const updateUser = useUpdateUser()
  const [reason, setReason] = useState('')
  const [until, setUntil] = useState('')

  useEffect(() => {
    if (!open || !user) return
    setReason(user.blocked_reason ?? '')
    setUntil(user.blocked_until ? user.blocked_until.slice(0, 16) : '')
  }, [open, user])

  const isBlocked = !!user?.is_blocked

  async function submit(block: boolean) {
    if (!user) return
    try {
      await updateUser.mutateAsync({
        username: user.username,
        body: {
          is_blocked: block,
          blocked_reason: block ? reason || 'Bloqué par un administrateur' : null,
          blocked_until: block && until ? new Date(until).toISOString() : null,
        },
      })
      toast.success(block ? 'Compte bloqué' : 'Compte débloqué')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{isBlocked ? 'Débloquer le compte' : 'Bloquer le compte'}</DialogTitle>
          <DialogDescription>Compte « {user?.username} »</DialogDescription>
        </DialogHeader>

        {!isBlocked && (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="block-reason">Raison</Label>
              <Input
                id="block-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Motif du blocage"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="block-until">Jusqu'au <span className="text-muted-foreground font-normal">(optionnel)</span></Label>
              <Input id="block-until" type="datetime-local" value={until} onChange={(e) => setUntil(e.target.value)} />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateUser.isPending}>
            Annuler
          </Button>
          <Button
            variant={isBlocked ? 'default' : 'destructive'}
            onClick={() => submit(!isBlocked)}
            disabled={updateUser.isPending}
          >
            {updateUser.isPending && <Loader2 className="size-4 animate-spin" />}
            {isBlocked ? 'Débloquer' : 'Bloquer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
