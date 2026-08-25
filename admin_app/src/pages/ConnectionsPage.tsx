import { useState } from 'react'
import { toast } from 'sonner'
import { Trash2 } from 'lucide-react'
import { useAccessLogs, useAccessStats, useClearAccessLogs, type ConnFilter } from '@/hooks/useAccessLogs'
import { getApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'medium' })
}

function statusVariant(code: number): 'default' | 'secondary' | 'destructive' {
  if (code >= 500) return 'destructive'
  if (code >= 400) return 'destructive'
  if (code >= 300) return 'secondary'
  return 'default'
}

export function ConnectionsPage() {
  const [filter, setFilter] = useState<ConnFilter>('all')
  const { data: stats } = useAccessStats()
  const { data: logs = [], isLoading } = useAccessLogs(filter)
  const clearLogs = useClearAccessLogs()

  async function handleClear() {
    try {
      await clearLogs.mutateAsync()
      toast.success('Historique vidé')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Connexions</h1>
          <p className="text-sm text-muted-foreground">Historique des requêtes reçues par l'API.</p>
        </div>
        <Button size="sm" variant="destructive" onClick={handleClear} disabled={clearLogs.isPending}>
          <Trash2 className="size-3.5" />
          Vider
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Requêtes totales" value={stats?.total} />
        <StatCard label="IPs uniques" value={stats?.unique_ips} className="text-info" />
        <StatCard label="Connectés" value={stats?.auth_count} className="text-primary" />
        <StatCard label="Visiteurs anonymes" value={stats?.anon_count} className="text-muted-foreground" />
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as ConnFilter)}>
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="all">Tous</TabsTrigger>
            <TabsTrigger value="auth">Connectés</TabsTrigger>
            <TabsTrigger value="anon">Visiteurs</TabsTrigger>
          </TabsList>
        </div>
      </Tabs>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>IP</TableHead>
              <TableHead>Utilisateur</TableHead>
              <TableHead>Méthode</TableHead>
              <TableHead>Chemin</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}
            {!isLoading && logs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">Aucune requête.</TableCell>
              </TableRow>
            )}
            {logs.map((log, i) => (
              <TableRow key={i}>
                <TableCell className="font-mono text-xs">{log.ip}</TableCell>
                <TableCell className="text-sm">{log.username ?? <span className="text-muted-foreground">anonyme</span>}</TableCell>
                <TableCell><Badge variant="outline">{log.method}</Badge></TableCell>
                <TableCell className="max-w-56 truncate text-sm text-muted-foreground" title={log.path}>{log.path}</TableCell>
                <TableCell><Badge variant={statusVariant(log.status_code)}>{log.status_code}</Badge></TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(log.timestamp)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function StatCard({ label, value, className }: { label: string; value: number | undefined; className?: string }) {
  return (
    <Card>
      <CardContent className="text-center">
        <p className={`text-2xl font-bold ${className ?? ''}`}>{value ?? '—'}</p>
        <p className="mt-1 text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}
