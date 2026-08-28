import { useState } from 'react'
import { toast } from 'sonner'
import { MoreHorizontal, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { useAdminCustomers, useUpdateCustomerStatus, useDeleteCustomer } from '@/hooks/useAdminCustomers'
import { getApiError } from '@/api/client'
import type { Customer } from '@/api/types'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { CustomerEditDialog } from './customers/CustomerEditDialog'
import { CustomerCreateDialog } from './customers/CustomerCreateDialog'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function CustomersAdminPage() {
  const { data: customers = [], isLoading } = useAdminCustomers()
  const updateStatus = useUpdateCustomerStatus()
  const deleteCustomer = useDeleteCustomer()
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)
  const [editTarget, setEditTarget] = useState<Customer | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Customer | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const filtered = customers.filter((c) => {
    if (!debouncedSearch) return true
    const term = debouncedSearch.toLowerCase()
    return c.username.toLowerCase().includes(term) || (c.email ?? '').toLowerCase().includes(term)
  })

  async function handleToggle(username: string, isActive: boolean) {
    try {
      await updateStatus.mutateAsync({ username, isActive })
      toast.success(isActive ? 'Client réactivé' : 'Client désactivé')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteCustomer.mutateAsync(deleteTarget.username)
      toast.success('Client supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Clients</h1>
          <p className="text-sm text-muted-foreground">Comptes clients de la boutique — création, modification, activation, désactivation et suppression.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="size-4" />
          Ajouter un client
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un client..." className="pl-8" />
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Client</TableHead>
              <TableHead>Rôle</TableHead>
              <TableHead>Créé le</TableHead>
              <TableHead>Actif</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}><Skeleton className="h-6 w-full" /></TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun client.
                </TableCell>
              </TableRow>
            )}

            {filtered.map((c) => (
              <TableRow key={c.username}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{c.username}</span>
                    {c.email && <span className="text-xs text-muted-foreground">{c.email}</span>}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={c.role === 'admin' ? 'default' : 'secondary'}>{c.role}</Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(c.created_at)}</TableCell>
                <TableCell>
                  <Switch
                    checked={c.is_active}
                    onCheckedChange={(v) => handleToggle(c.username, v)}
                    disabled={c.role === 'admin' || updateStatus.isPending}
                  />
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => setEditTarget(c)}>
                        <Pencil className="size-4" />
                        Modifier
                      </DropdownMenuItem>
                      {c.role !== 'admin' && (
                        <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(c)}>
                          <Trash2 className="size-4" />
                          Supprimer
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <CustomerCreateDialog open={createOpen} onOpenChange={setCreateOpen} />

      <CustomerEditDialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)} customer={editTarget} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer ce client ?"
        description={deleteTarget ? `« ${deleteTarget.username} » sera supprimé définitivement. Son accès Jellyfin sera désactivé si un abonnement est en cours.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteCustomer.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
