import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useCreateManualSubscription } from '@/hooks/useAdminSubscriptions'
import { useAdminPlans } from '@/hooks/useAdminPlans'
import { getApiError } from '@/api/client'
import type { SubscriptionAdmin } from '@/api/types'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface ManualSubscriptionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ManualSubscriptionDialog({ open, onOpenChange }: ManualSubscriptionDialogProps) {
  const { data: plans = [] } = useAdminPlans()
  const createManual = useCreateManualSubscription()

  const [username, setUsername] = useState('')
  const [planId, setPlanId] = useState('')
  const [durationDays, setDurationDays] = useState('')
  const [created, setCreated] = useState<SubscriptionAdmin | null>(null)

  function reset() {
    setUsername('')
    setPlanId('')
    setDurationDays('')
    setCreated(null)
  }

  async function handleSubmit() {
    if (!username.trim() || !planId) {
      toast.error('Client et palier requis')
      return
    }
    try {
      const result = await createManual.mutateAsync({
        username: username.trim(),
        planId,
        durationDays: durationDays ? Number(durationDays) : undefined,
      })
      if (result.jellyfin_initial_password_pending) {
        setCreated(result)
      } else {
        toast.success('Abonnement ajouté — accès Jellyfin provisionné')
        reset()
        onOpenChange(false)
      }
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  function handleClose(v: boolean) {
    if (!v) reset()
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ajouter un abonnement manuellement</DialogTitle>
          <DialogDescription>
            Geste commercial ou compensation — active l'accès Jellyfin directement, sans passer par PayPal.
          </DialogDescription>
        </DialogHeader>

        {created ? (
          <div className="space-y-4">
            <Alert>
              <AlertTitle>Accès Jellyfin créé</AlertTitle>
              <AlertDescription>
                <p>Nom d'utilisateur Jellyfin : <span className="font-mono">{created.jellyfin_username}</span></p>
                <p>Mot de passe initial : <span className="font-mono">{created.jellyfin_initial_password_pending}</span></p>
                <p className="mt-1 text-xs">
                  Notez-le maintenant et transmettez-le au client — il ne sera plus jamais affiché ici
                  (il reste toutefois visible une fois sur la page « Mon abonnement » du client s'il se
                  connecte à la boutique avant vous).
                </p>
              </AlertDescription>
            </Alert>
            <DialogFooter>
              <Button onClick={() => { reset(); onOpenChange(false) }}>Fermer</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="manual-username">Nom d'utilisateur du client</Label>
                <Input id="manual-username" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
              </div>

              <div className="space-y-1.5">
                <Label>Palier</Label>
                <Select value={planId} onValueChange={(v) => setPlanId(v ?? '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un palier..." />
                  </SelectTrigger>
                  <SelectContent>
                    {plans.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name} — {p.duration_days} j</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="manual-duration">Durée (jours) — optionnel</Label>
                <Input
                  id="manual-duration"
                  type="number"
                  min={1}
                  placeholder="Durée du palier par défaut"
                  value={durationDays}
                  onChange={(e) => setDurationDays(e.target.value)}
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
              <Button onClick={handleSubmit} disabled={createManual.isPending}>
                {createManual.isPending && <Loader2 className="size-4 animate-spin" />}
                Ajouter
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
