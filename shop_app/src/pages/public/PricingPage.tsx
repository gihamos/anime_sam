import { useNavigate } from 'react-router-dom'
import { Check, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { usePlans } from '@/hooks/usePlans'
import { useSubscribe } from '@/hooks/useSubscription'
import { useAuthStore } from '@/stores/auth'
import { getApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function PricingPage() {
  const { data: plans, isLoading } = usePlans()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const subscribe = useSubscribe()
  const navigate = useNavigate()

  async function handleSubscribe(planId: string) {
    if (!isAuthenticated) {
      navigate('/connexion')
      return
    }
    try {
      const { approval_url } = await subscribe.mutateAsync(planId)
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
                <div className="pt-2">
                  <span className="text-3xl font-semibold">{plan.price.toFixed(2)} {plan.currency}</span>
                  <span className="text-sm text-muted-foreground"> / {plan.billing_period === 'month' ? 'mois' : 'an'}</span>
                </div>
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
