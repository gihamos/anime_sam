import { useMyPayments } from '@/hooks/useSubscription'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function BillingHistoryPage() {
  const { data: payments, isLoading } = useMyPayments()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Facturation</h1>
        <p className="text-sm text-muted-foreground">Historique de vos paiements.</p>
      </div>

      {isLoading && <Skeleton className="h-40 rounded-lg" />}

      {!isLoading && (
        <Card>
          <CardContent className="p-0">
            {!payments || payments.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">Aucun paiement enregistré pour le moment.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Montant</TableHead>
                    <TableHead>Statut</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell>{formatDate(p.paid_at)}</TableCell>
                      <TableCell>{p.amount.toFixed(2)} {p.currency}</TableCell>
                      <TableCell>
                        <Badge variant={p.status === 'completed' ? 'default' : 'secondary'}>{p.status}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
