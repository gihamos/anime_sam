import { Link } from 'react-router-dom'
import { AlertTriangle, ExternalLink, KeyRound } from 'lucide-react'
import { useMySubscription } from '@/hooks/useSubscription'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const STATUS_LABELS: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' }> = {
  pending:   { label: 'En attente de paiement', variant: 'secondary' },
  active:    { label: 'Actif', variant: 'default' },
  past_due:  { label: 'Paiement en retard', variant: 'destructive' },
  suspended: { label: 'Suspendu', variant: 'destructive' },
  cancelled: { label: 'Annulé', variant: 'secondary' },
  expired:   { label: 'Expiré', variant: 'secondary' },
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function AccountOverviewPage() {
  const { data: subscription, isLoading } = useMySubscription()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Mon compte</h1>
        <p className="text-sm text-muted-foreground">Aperçu de votre abonnement et de votre accès au serveur Jellyfin.</p>
      </div>

      {isLoading && <Skeleton className="h-48 rounded-lg" />}

      {!isLoading && !subscription && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm text-muted-foreground">Vous n'avez pas encore d'abonnement actif.</p>
            <Button render={<Link to="/tarifs" />} nativeButton={false}>
              Voir les tarifs
            </Button>
          </CardContent>
        </Card>
      )}

      {!isLoading && subscription && (
        <>
          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <h2 className="text-base font-semibold">{subscription.plan_name ?? 'Palier'}</h2>
                <p className="text-sm text-muted-foreground">Renouvellement le {formatDate(subscription.current_period_end)}</p>
              </div>
              <Badge variant={STATUS_LABELS[subscription.status]?.variant ?? 'secondary'}>
                {STATUS_LABELS[subscription.status]?.label ?? subscription.status}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              {subscription.cancel_at_period_end && (
                <Alert>
                  <AlertTriangle className="size-4" />
                  <AlertTitle>Abonnement annulé</AlertTitle>
                  <AlertDescription>
                    Votre accès reste actif jusqu'au {formatDate(subscription.current_period_end)}, puis sera désactivé automatiquement.
                  </AlertDescription>
                </Alert>
              )}

              {subscription.jellyfin_initial_password_pending && (
                <Alert>
                  <KeyRound className="size-4" />
                  <AlertTitle>Identifiants Jellyfin</AlertTitle>
                  <AlertDescription>
                    <p>Nom d'utilisateur : <span className="font-mono">{subscription.jellyfin_username}</span></p>
                    <p>Mot de passe initial : <span className="font-mono">{subscription.jellyfin_initial_password_pending}</span></p>
                    <p className="mt-1 text-xs">
                      Notez-le maintenant — il ne sera plus jamais affiché. Vous pourrez le réinitialiser
                      à tout moment depuis la page de gestion de compte Jellyfin.
                    </p>
                  </AlertDescription>
                </Alert>
              )}

              {subscription.jellyfin_username && !subscription.jellyfin_initial_password_pending && (
                <p className="text-sm text-muted-foreground">
                  Compte Jellyfin : <span className="font-mono text-foreground">{subscription.jellyfin_username}</span>
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" render={<Link to="/compte/abonnement" />} nativeButton={false}>
                  Gérer mon palier
                </Button>
                {subscription.jellyfin_username && (
                  <Button
                    variant="ghost"
                    size="sm"
                    render={<a href="https://account.gihamos.fr/my/account" target="_blank" rel="noreferrer" />}
                    nativeButton={false}
                  >
                    Réinitialiser mon mot de passe Jellyfin
                    <ExternalLink className="size-3.5" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
