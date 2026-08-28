import type { PlanPopularity } from '@/api/types'

export function PlanPopularityList({ data }: { data: PlanPopularity[] }) {
  if (data.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Aucun abonnement actif pour le moment.</p>
  }

  const max = Math.max(...data.map((d) => d.count))

  return (
    <div className="space-y-3">
      {data.map((plan) => (
        <div key={plan.plan_id} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{plan.plan_name}</span>
            <span className="text-muted-foreground">{plan.count} abonné{plan.count > 1 ? 's' : ''}</span>
          </div>
          <div className="h-2 rounded-full bg-muted">
            <div
              className="h-2 rounded-full bg-primary"
              style={{ width: `${Math.max((plan.count / max) * 100, 4)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
