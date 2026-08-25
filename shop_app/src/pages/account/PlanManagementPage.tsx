import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useMySubscription, useCancelSubscription, useChangePlan } from '@/hooks/useSubscription'
import { usePlans } from '@/hooks/usePlans'
import { getApiError } from '@/api/client'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'

export function PlanManagementPage() {
  const { data: subscription, isLoading } = useMySubscription()
  const { data: plans } = usePlans()
  const cancelSubscription = useCancelSubscription()
  const changePlan = useChangePlan()
  const [confirmOpen, setConfirmOpen] = useState(false)

  async function handleCancel() {
    try {
      await cancelSubscription.mutateAsync(undefined)
      toast.success('Abonnement annulé — accès conservé jusqu\'à la fin de la période payée')
      setConfirmOpen(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleChangePlan(planId: string) {
    try {
      await changePlan.mutateAsync(planId)
      toast.success('Palier mis à jour')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  if (isLoading) return <Skeleton className="h-64 rounded-lg" />

  if (!subscription) {
    return <p className="text-sm text-muted-foreground">Aucun abonnement à gérer.</p>
  }

  const otherPlans = (plans ?? []).filter((p) => p.id !== subscription.plan_id)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Gérer mon abonnement</h1>
        <p className="text-sm text-muted-foreground">Changez de palier ou annulez votre abonnement.</p>
      </div>

      {subscription.status === 'active' && otherPlans.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Changer de palier</h2>
          </CardHeader>
          <CardContent className="space-y-3">
            {otherPlans.map((p) => (
              <div key={p.id} className="flex items-center justify-between rounded-md border border-border p-3">
                <div>
                  <p className="text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-muted-foreground">{p.price.toFixed(2)} {p.currency} / {p.billing_period === 'month' ? 'mois' : 'an'}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => handleChangePlan(p.id)} disabled={changePlan.isPending}>
                  {changePlan.isPending && <Loader2 className="size-4 animate-spin" />}
                  Choisir
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {!subscription.cancel_at_period_end && subscription.status !== 'cancelled' && subscription.status !== 'expired' && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Annuler mon abonnement</h2>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Votre accès restera actif jusqu'à la fin de la période déjà payée, puis sera désactivé automatiquement.
            </p>
            <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
              <DialogTrigger render={<Button variant="destructive" />}>
                Annuler mon abonnement
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Confirmer l'annulation</DialogTitle>
                  <DialogDescription>
                    Cette action arrête le renouvellement automatique. Votre accès reste actif jusqu'à la fin de la période déjà payée.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setConfirmOpen(false)}>Retour</Button>
                  <Button variant="destructive" onClick={handleCancel} disabled={cancelSubscription.isPending}>
                    {cancelSubscription.isPending && <Loader2 className="size-4 animate-spin" />}
                    Confirmer l'annulation
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
