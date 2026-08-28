import { useAdminStats } from '@/hooks/useAdminStats'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { RevenueChart } from './stats/RevenueChart'
import { PlanPopularityList } from './stats/PlanPopularityList'

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  active: 'Actifs',
  past_due: 'Paiement en retard',
  suspended: 'Suspendus',
  cancelled: 'Résiliés',
  expired: 'Expirés',
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  )
}

export function StatsAdminPage() {
  const { data: stats, isLoading } = useAdminStats()

  if (isLoading || !stats) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Statistiques</h1>
          <p className="text-sm text-muted-foreground">Ventes et utilisation de la boutique.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
        <Skeleton className="h-64 rounded-lg" />
      </div>
    )
  }

  const currency = 'EUR'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Statistiques</h1>
        <p className="text-sm text-muted-foreground">Ventes et utilisation de la boutique.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Chiffre d'affaires total" value={`${stats.total_revenue.toFixed(2)} ${currency}`} />
        <StatTile label="Chiffre d'affaires du mois" value={`${stats.month_revenue.toFixed(2)} ${currency}`} />
        <StatTile label="Abonnements actifs" value={String(stats.active_subscriptions)} />
        <StatTile label="Clients" value={`${stats.total_customers} (+${stats.new_customers_this_month} ce mois)`} />
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Revenus des 30 derniers jours</h2>
        </CardHeader>
        <CardContent>
          <RevenueChart data={stats.daily_revenue} currency={currency} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Paliers les plus populaires</h2>
          </CardHeader>
          <CardContent>
            <PlanPopularityList data={stats.plan_popularity} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Répartition des abonnements</h2>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(stats.subscriptions_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{STATUS_LABELS[status] ?? status}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(stats.subscriptions_by_status).length === 0 && (
              <p className="text-sm text-muted-foreground">Aucun abonnement enregistré.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
