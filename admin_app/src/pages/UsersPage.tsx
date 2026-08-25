import { useState } from 'react'
import { toast } from 'sonner'
import {
  Ban,
  Download,
  MoreHorizontal,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  UserRoundCog,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useDeleteUser, useUsers } from '@/hooks/useUsers'
import { getApiError } from '@/api/client'
import type { Role, User } from '@/api/types'
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
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { UserFormDialog } from './users/UserFormDialog'
import { AccessDialog } from './users/AccessDialog'
import { DownloadPermsDialog } from './users/DownloadPermsDialog'
import { BlockDialog } from './users/BlockDialog'

type RoleFilter = Role | 'all'
type DialogKind = 'form' | 'access' | 'dl-perms' | 'block' | null

export function UsersPage() {
  const currentUsername = useAuthStore((s) => s.user?.username)
  const { data: users = [], isLoading } = useUsers()
  const deleteUser = useDeleteUser()

  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [dialog, setDialog] = useState<DialogKind>(null)
  const [activeUser, setActiveUser] = useState<User | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)

  const filtered = users.filter((u) => {
    if (roleFilter !== 'all' && u.role !== roleFilter) return false
    if (search && !u.username.toLowerCase().includes(search.toLowerCase()) && !(u.email ?? '').toLowerCase().includes(search.toLowerCase())) {
      return false
    }
    return true
  })

  function openDialog(kind: DialogKind, user: User | null) {
    setActiveUser(user)
    setDialog(kind)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteUser.mutateAsync(deleteTarget.username)
      toast.success('Utilisateur supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Utilisateurs</h1>
          <p className="text-sm text-muted-foreground">Comptes, accès et permissions.</p>
        </div>
        <Button onClick={() => openDialog('form', null)}>
          <Plus className="size-4" />
          Ajouter
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un utilisateur..."
            className="pl-8"
          />
        </div>
        <Select value={roleFilter} onValueChange={(v) => setRoleFilter(v as RoleFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les rôles</SelectItem>
            <SelectItem value="admin">Administrateurs</SelectItem>
            <SelectItem value="user">Utilisateurs</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Utilisateur</TableHead>
              <TableHead>Rôle</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Accès</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun utilisateur trouvé.
                </TableCell>
              </TableRow>
            )}

            {filtered.map((user) => (
              <TableRow key={user.username}>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{user.username}</span>
                    {user.email && <span className="text-xs text-muted-foreground">{user.email}</span>}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                    {user.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
                  </Badge>
                </TableCell>
                <TableCell>
                  {user.is_blocked ? (
                    <Badge variant="destructive">Bloqué</Badge>
                  ) : user.is_active ? (
                    <Badge className="bg-success text-success-foreground">Actif</Badge>
                  ) : (
                    <Badge variant="secondary">Inactif</Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {user.permissions.allowed_catalogues.length === 0
                    ? 'Tous les catalogues'
                    : `${user.permissions.allowed_catalogues.length} catalogue(s)`}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                      <MoreHorizontal className="size-4" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openDialog('form', user)}>
                        <UserRoundCog className="size-4" />
                        Modifier
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('access', user)}>
                        <ShieldCheck className="size-4" />
                        Accès aux catalogues
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('dl-perms', user)}>
                        <Download className="size-4" />
                        Téléchargement
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => openDialog('block', user)}>
                        <Ban className="size-4" />
                        {user.is_blocked ? 'Débloquer' : 'Bloquer'}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        variant="destructive"
                        disabled={user.username === currentUsername}
                        onClick={() => setDeleteTarget(user)}
                      >
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

      <UserFormDialog open={dialog === 'form'} onOpenChange={(v) => setDialog(v ? 'form' : null)} user={activeUser} />
      <AccessDialog open={dialog === 'access'} onOpenChange={(v) => setDialog(v ? 'access' : null)} user={activeUser} />
      <DownloadPermsDialog open={dialog === 'dl-perms'} onOpenChange={(v) => setDialog(v ? 'dl-perms' : null)} user={activeUser} />
      <BlockDialog open={dialog === 'block'} onOpenChange={(v) => setDialog(v ? 'block' : null)} user={activeUser} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer cet utilisateur ?"
        description={deleteTarget ? `« ${deleteTarget.username} » sera définitivement supprimé. Cette action est irréversible.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteUser.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
