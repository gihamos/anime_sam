import { useState } from 'react'
import { toast } from 'sonner'
import { MoreHorizontal, Plus, RefreshCw, Search, ShieldCheck, Trash2 } from 'lucide-react'
import { useApiClients, useDeleteApiClient, useRegenerateApiClientSecret } from '@/hooks/useApiClients'
import { getApiError } from '@/api/client'
import type { ApiClient } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { ClientFormDialog } from './applications/ClientFormDialog'
import { ClientAccessDialog } from './applications/ClientAccessDialog'
import { SecretDialog } from './applications/SecretDialog'

type StatusFilter = 'all' | 'active' | 'inactive'
type DialogKind = 'form' | 'access' | null

export function ApplicationsPage() {
  const { data: clients = [], isLoading } = useApiClients()
  const deleteClient = useDeleteApiClient()
  const regenerateSecret = useRegenerateApiClientSecret()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [dialog, setDialog] = useState<DialogKind>(null)
  const [activeClient, setActiveClient] = useState<ApiClient | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ApiClient | null>(null)
  const [secret, setSecret] = useState<{ clientId: string; clientSecret: string } | null>(null)

  const filtered = clients.filter((c) => {
    if (statusFilter === 'active' && !c.is_active) return false
    if (statusFilter === 'inactive' && c.is_active) return false
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  function openDialog(kind: DialogKind, client: ApiClient | null) {
    setActiveClient(client)
    setDialog(kind)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteClient.mutateAsync(deleteTarget.client_id)
      toast.success('Application supprimée')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleRegenerate(client: ApiClient) {
    try {
      const res = await regenerateSecret.mutateAsync(client.client_id)
      setSecret({ clientId: res.client_id, clientSecret: res.client_secret })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Applications</h1>
          <p className="text-sm text-muted-foreground">Clients API tiers (machine-à-machine).</p>
        </div>
        <Button onClick={() => openDialog('form', null)}>
          <Plus className="size-4" />
          Ajouter
        </Button>
      </div>

      <Alert>
        <ShieldCheck className="size-4" />
        <AlertDescription>
          Ces applications s'authentifient via <code>POST /auth/client-token</code> avec leur client_id et client_secret.
        </AlertDescription>
      </Alert>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher par nom..." className="pl-8" />
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous statuts</SelectItem>
            <SelectItem value="active">Actif</SelectItem>
            <SelectItem value="inactive">Inactif</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Application</TableHead>
              <TableHead>Client ID</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Accès</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucune application.
                </TableCell>
              </TableRow>
            )}

            {filtered.map((client) => (
              <TableRow key={client.client_id}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{client.name}</span>
                    {client.description && <span className="text-xs text-muted-foreground">{client.description}</span>}
                  </div>
                </TableCell>
                <TableCell>
                  <code className="text-xs text-muted-foreground">{client.client_id}</code>
                </TableCell>
                <TableCell>
                  {client.is_active ? (
                    <Badge className="bg-success text-success-foreground">Actif</Badge>
                  ) : (
                    <Badge variant="secondary">Inactif</Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {client.permissions.allowed_catalogues.length === 0
                    ? 'Tous les catalogues'
                    : `${client.permissions.allowed_catalogues.length} catalogue(s)`}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openDialog('form', client)}>Modifier</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('access', client)}>Accès aux catalogues</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleRegenerate(client)}>
                        <RefreshCw className="size-4" />
                        Régénérer le secret
                      </DropdownMenuItem>
                      <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(client)}>
                        <Trash2 className="size-4" />
                        Supprimer
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ClientFormDialog
        open={dialog === 'form'}
        onOpenChange={(v) => setDialog(v ? 'form' : null)}
        client={activeClient}
        onCreated={(created) => setSecret({ clientId: created.client_id, clientSecret: created.client_secret })}
      />
      <ClientAccessDialog open={dialog === 'access'} onOpenChange={(v) => setDialog(v ? 'access' : null)} client={activeClient} />
      <SecretDialog
        open={!!secret}
        onOpenChange={(v) => !v && setSecret(null)}
        clientId={secret?.clientId ?? null}
        clientSecret={secret?.clientSecret ?? null}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer cette application ?"
        description={deleteTarget ? `« ${deleteTarget.name} » ne pourra plus s'authentifier.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteClient.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
