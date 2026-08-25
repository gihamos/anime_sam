import { useState } from 'react'
import { Loader2, UserMinus } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useAddGroupMember, useGroupMembers, useRemoveGroupMember } from '@/hooks/useGroups'
import type { Group } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface GroupMembersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  group: Group | null
}

export function GroupMembersDialog({ open, onOpenChange, group }: GroupMembersDialogProps) {
  const [username, setUsername] = useState('')
  const { data: members = [], isLoading } = useGroupMembers(open ? group?.id ?? null : null)
  const addMember = useAddGroupMember()
  const removeMember = useRemoveGroupMember()

  async function handleAdd() {
    if (!group || !username.trim()) return
    try {
      await addMember.mutateAsync({ groupId: group.id, username: username.trim() })
      setUsername('')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleRemove(u: string) {
    if (!group) return
    try {
      await removeMember.mutateAsync({ groupId: group.id, username: u })
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Membres</DialogTitle>
        </DialogHeader>

        <div className="flex gap-2">
          <Input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Nom d'utilisateur à ajouter..."
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <Button onClick={handleAdd} disabled={!username.trim() || addMember.isPending}>
            {addMember.isPending && <Loader2 className="size-4 animate-spin" />}
            Ajouter
          </Button>
        </div>

        {isLoading && <Skeleton className="h-32 w-full" />}

        {!isLoading && (
          <ScrollArea className="h-64 rounded-lg border border-border">
            <div className="divide-y divide-border">
              {members.map((m) => (
                <div key={m.username} className="flex items-center justify-between px-3 py-2">
                  <span className="text-sm font-medium">{m.username}</span>
                  <Button size="icon-sm" variant="ghost" onClick={() => handleRemove(m.username)} disabled={removeMember.isPending}>
                    <UserMinus className="size-3.5" />
                  </Button>
                </div>
              ))}
              {members.length === 0 && (
                <p className="px-3 py-8 text-center text-sm text-muted-foreground">Aucun membre.</p>
              )}
            </div>
          </ScrollArea>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Fermer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
