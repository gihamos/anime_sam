import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { useConfirmSubscription } from '@/hooks/useSubscription'
import { getApiError } from '@/api/client'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function CheckoutReturnPage() {
  const [searchParams] = useSearchParams()
  const subscriptionId = searchParams.get('subscription_id')
  const confirm = useConfirmSubscription()
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!subscriptionId) {
      setStatus('error')
      setError('Identifiant d\'abonnement manquant dans le retour PayPal')
      return
    }
    confirm.mutate(subscriptionId, {
      onSuccess: () => setStatus('ok'),
      onError: (err) => {
        setStatus('error')
        setError(getApiError(err))
      },
    })
  }, [subscriptionId]) // eslint/oxlint: confirm() intentionally excluded — mutate identity is stable, re-running on it would loop

  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          {status === 'loading' && <Loader2 className="size-8 animate-spin text-muted-foreground" />}
          {status === 'ok' && <CheckCircle2 className="size-8 text-primary" />}
          {status === 'error' && <XCircle className="size-8 text-destructive" />}
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          {status === 'loading' && <p className="text-sm text-muted-foreground">Confirmation de votre abonnement en cours...</p>}
          {status === 'ok' && (
            <>
              <p className="text-sm">Votre abonnement est actif. Votre accès Jellyfin est prêt.</p>
              <Button className="w-full" render={<Link to="/compte" />} nativeButton={false}>
                Voir mon compte
              </Button>
            </>
          )}
          {status === 'error' && (
            <>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button variant="outline" className="w-full" render={<Link to="/compte" />} nativeButton={false}>
                Retour à mon compte
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
