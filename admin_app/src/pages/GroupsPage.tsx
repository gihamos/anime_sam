import { useState } from 'react'
import { toast } from 'sonner'
import { Library, MoreHorizontal, Plus, Search, Tag, Trash2, UserCog, Users } from 'lucide-react'
import { useDeleteGroup, useGroups } from '@/hooks/useGroups'
import { getApiError } from '@/api/client'
import type { Group, GroupType } from '@/api/types'
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
import { GroupFormDialog } from './groups/GroupFormDialog'
import { GroupMembersDialog } from './groups/GroupMembersDialog'

type TypeFilter = GroupType | 'all'
type DialogKind = 'form' | 'members' | null

const TYPE_ICONS: Record<GroupType, typeof Library> = {
  catalogue: Library,
  genre: Tag,
  permission: UserCog,
}

const TYPE_LABELS: Record<GroupType, string> = {
  catalogue: 'Catalogues',
  genre: 'Genres',
  permission: 'Permissions',
}

export function GroupsPage() {
  const { data: groups = [], isLoading } = useGroups()
  const deleteGroup = useDeleteGroup()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [dialog, setDialog] = useState<DialogKind>(null)
  const [activeGroup, setActiveGroup] = useState<Group | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Group | null>(null)

  const filtered = groups.filter((g) => {
    if (typeFilter !== 'all' && g.type !== typeFilter) return false
    if (search && !g.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  function openDialog(kind: DialogKind, group: Group | null) {
    setActiveGroup(group)
    setDialog(kind)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteGroup.mutateAsync(deleteTarget.id)
      toast.success('Groupe supprimé')
      setDeleteTarget(null)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Groupes</h1>
          <p className="text-sm text-muted-foreground">Accès et permissions partagés entre plusieurs utilisateurs.</p>
        </div>
        <Button onClick={() => openDialog('form', null)}>
          <Plus className="size-4" />
          Ajouter
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un groupe..." className="pl-8" />
        </div>
        <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as TypeFilter)}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous types</SelectItem>
            <SelectItem value="catalogue">Catalogues</SelectItem>
            <SelectItem value="genre">Genres</SelectItem>
            <SelectItem value="permission">Permissions</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Détails</TableHead>
              <TableHead>Membres</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Aucun groupe.
                </TableCell>
              </TableRow>
            )}

            {filtered.map((group) => {
              const Icon = TYPE_ICONS[group.type]
              return (
                <TableRow key={group.id}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium">{group.name}</span>
                      {group.description && <span className="text-xs text-muted-foreground">{group.description}</span>}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="gap-1">
                      <Icon className="size-3" />
                      {TYPE_LABELS[group.type]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {group.type === 'catalogue' && `${group.catalogue_slugs.length} catalogue(s)`}
                    {group.type === 'genre' && `${group.genres.length} genre(s)`}
                    {group.type === 'permission' && 'Permissions seules'}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => openDialog('members', group)}>
                      <Users className="size-3.5" />
                      {group.member_count}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
                        <MoreHorizontal className="size-4" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openDialog('form', group)}>Modifier</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => openDialog('members', group)}>Membres</DropdownMenuItem>
                        <DropdownMenuItem variant="destructive" onClick={() => setDeleteTarget(group)}>
                          <Trash2 className="size-4" />
                          Supprimer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <GroupFormDialog open={dialog === 'form'} onOpenChange={(v) => setDialog(v ? 'form' : null)} group={activeGroup} />
      <GroupMembersDialog open={dialog === 'members'} onOpenChange={(v) => setDialog(v ? 'members' : null)} group={activeGroup} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Supprimer ce groupe ?"
        description={deleteTarget ? `« ${deleteTarget.name} » sera supprimé. Les membres perdront les accès associés.` : undefined}
        confirmLabel="Supprimer"
        destructive
        isPending={deleteGroup.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}
