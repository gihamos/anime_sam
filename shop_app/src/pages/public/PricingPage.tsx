import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, Loader2, Tag } from 'lucide-react'
import { toast } from 'sonner'
import { usePlans } from '@/hooks/usePlans'
import { useSubscribe, usePromoPreview } from '@/hooks/useSubscription'
import { useAuthStore } from '@/stores/auth'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { getApiError } from '@/api/client'
import type { Plan } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

function formatDeadline(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
}

function PlanPrice({ plan, promoCode }: { plan: Plan; promoCode: string }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { data: preview } = usePromoPreview(isAuthenticated ? promoCode : '', plan.id)

  // Le code promo (s'il est valide) s'applique par-dessus la réduction déjà active sur le
  // palier — la prévisualisation renvoyée par le serveur reflète déjà les deux cumulées.
  if (preview) {
    return (
      <div className="pt-2">
        <span className="text-sm text-muted-foreground line-through">{plan.price.toFixed(2)} {plan.currency}</span>
        <div>
          <span className="text-3xl font-semibold text-primary">{preview.discounted_price.toFixed(2)} {preview.currency}</span>
          <span className="text-sm text-muted-foreground"> / {plan.duration_days} jours</span>
        </div>
      </div>
    )
  }

  if (plan.discounted_price !== null) {
    return (
      <div className="pt-2">
        <span className="text-sm text-muted-foreground line-through">{plan.price.toFixed(2)} {plan.currency}</span>
        <div>
          <span className="text-3xl font-semibold text-primary">{plan.discounted_price.toFixed(2)} {plan.currency}</span>
          <span className="text-sm text-muted-foreground"> / {plan.duration_days} jours</span>
        </div>
        {plan.discount_expires_at && (
          <p className="mt-0.5 text-xs text-primary">Offre valable jusqu'au {formatDeadline(plan.discount_expires_at)}</p>
        )}
      </div>
    )
  }

  return (
    <div className="pt-2">
      <span className="text-3xl font-semibold">{plan.price.toFixed(2)} {plan.currency}</span>
      <span className="text-sm text-muted-foreground"> / {plan.duration_days} jours</span>
    </div>
  )
}

export function PricingPage() {
  const { data: plans, isLoading } = usePlans()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const subscribe = useSubscribe()
  const navigate = useNavigate()
  const [autoRenew, setAutoRenew] = useState(true)
  const [promoInput, setPromoInput] = useState('')
  const promoCode = useDebouncedValue(promoInput.trim().toUpperCase(), 400)

  async function handleSubscribe(planId: string) {
    if (!isAuthenticated) {
      navigate('/connexion')
      return
    }
    try {
      const { approval_url } = await subscribe.mutateAsync({ planId, autoRenew, promoCode: promoCode || undefined })
      window.location.href = approval_url
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
      <div className="mb-10 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Tarifs</h1>
        <p className="mt-2 text-muted-foreground">Choisissez le palier adapté à votre usage. Sans engagement, résiliable à tout moment.</p>
      </div>

      {!isLoading && plans && plans.length > 0 && (
        <div className="mb-8 space-y-3">
          <div className="flex items-center justify-center gap-3 rounded-lg border border-border bg-card p-4">
            <Switch id="auto-renew" checked={autoRenew} onCheckedChange={setAutoRenew} />
            <Label htmlFor="auto-renew" className="cursor-pointer">
              Renouvellement automatique
              <span className="ml-2 font-normal text-muted-foreground">
                {autoRenew
                  ? "votre abonnement se renouvelle tout seul jusqu'à ce que vous l'annuliez"
                  : "paiement unique, accès non reconduit à l'échéance"}
              </span>
            </Label>
          </div>

          <div className="mx-auto flex max-w-sm items-center gap-2 rounded-lg border border-border bg-card p-3">
            <Tag className="size-4 shrink-0 text-muted-foreground" />
            <Input
              placeholder="Code promo"
              value={promoInput}
              onChange={(e) => setPromoInput(e.target.value)}
              className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
            />
          </div>
        </div>
      )}

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-80 rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && plans && plans.length === 0 && (
        <p className="text-center text-sm text-muted-foreground">Aucun palier n'est disponible pour le moment.</p>
      )}

      {!isLoading && plans && plans.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          {plans.map((plan) => (
            <Card key={plan.id} className="flex flex-col">
              <CardHeader>
                <h2 className="text-base font-semibold">{plan.name}</h2>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
                <PlanPrice plan={plan} promoCode={promoCode} />
              </CardHeader>
              <CardContent className="flex flex-1 flex-col justify-between gap-4">
                <ul className="space-y-2 text-sm">
                  {plan.jellyfin_library_names.map((name) => (
                    <li key={name} className="flex items-center gap-2">
                      <Check className="size-4 shrink-0 text-primary" />
                      {name}
                    </li>
                  ))}
                  <li className="flex items-center gap-2">
                    <Check className="size-4 shrink-0 text-primary" />
                    {plan.max_devices} appareil{plan.max_devices > 1 ? 's' : ''} simultané{plan.max_devices > 1 ? 's' : ''}
                  </li>
                  {plan.allow_downloads && (
                    <li className="flex items-center gap-2">
                      <Check className="size-4 shrink-0 text-primary" />
                      Téléchargement hors ligne
                    </li>
                  )}
                </ul>
                <Button
                  className="w-full"
                  onClick={() => handleSubscribe(plan.id)}
                  disabled={subscribe.isPending}
                >
                  {subscribe.isPending && <Loader2 className="size-4 animate-spin" />}
                  S'abonner
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
