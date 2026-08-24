import { type FormEvent, useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCreateUser, useUpdateUser } from '@/hooks/useUsers'
import type { QuotaConfig, Role, User } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const DEFAULT_QUOTA: QuotaConfig = { enabled: false, period: 'day', max_syncs: 10 }

interface UserFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
}

export function UserFormDialog({ open, onOpenChange, user }: UserFormDialogProps) {
  const isEdit = !!user
  const createUser = useCreateUser()
  const updateUser = useUpdateUser()
  const isPending = createUser.isPending || updateUser.isPending

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('user')
  const [isActive, setIsActive] = useState(true)
  const [canSync, setCanSync] = useState(false)
  const [canDelete, setCanDelete] = useState(false)
  const [canRefresh, setCanRefresh] = useState(false)
  const [quota, setQuota] = useState<QuotaConfig>(DEFAULT_QUOTA)

  useEffect(() => {
    if (!open) return
    if (user) {
      setUsername(user.username)
      setEmail(user.email ?? '')
      setPassword('')
      setRole(user.role)
      setIsActive(user.is_active)
      setCanSync(user.permissions.can_sync)
      setCanDelete(user.permissions.can_delete)
      setCanRefresh(user.permissions.can_refresh)
      setQuota(user.permissions.quota ?? DEFAULT_QUOTA)
    } else {
      setUsername('')
      setEmail('')
      setPassword('')
      setRole('user')
      setIsActive(true)
      setCanSync(false)
      setCanDelete(false)
      setCanRefresh(false)
      setQuota(DEFAULT_QUOTA)
    }
  }, [open, user])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      if (isEdit && user) {
        await updateUser.mutateAsync({
          username: user.username,
          body: {
            email: email || undefined,
            password: password || undefined,
            role,
            is_active: isActive,
            permissions: {
              ...user.permissions,
              can_sync: canSync,
              can_delete: canDelete,
              can_refresh: canRefresh,
              quota,
            },
          },
        })
        toast.success('Utilisateur mis à jour')
      } else {
        if (!username.trim() || !password) {
          toast.error("Nom d'utilisateur et mot de passe requis")
          return
        }
        await createUser.mutateAsync({
          username: username.trim(),
          password,
          email: email || undefined,
          role,
          permissions: {
            can_sync: canSync,
            can_delete: canDelete,
            can_refresh: canRefresh,
            can_download: true,
            allowed_catalogues: [],
            catalogue_content: {},
            quota,
          },
        })
        toast.success('Utilisateur créé')
      }
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Modifier l'utilisateur" : 'Nouvel utilisateur'}</DialogTitle>
          <DialogDescription>
            {isEdit ? `Compte « ${user?.username} »` : 'Crée un compte avec un accès immédiat.'}
          </DialogDescription>
        </DialogHeader>
        <form id="user-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="uf-username">Nom d'utilisateur</Label>
              <Input
                id="uf-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isEdit}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="uf-email">Email</Label>
              <Input id="uf-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="uf-password">Mot de passe {isEdit && <span className="text-muted-foreground font-normal">(laisser vide pour ne pas changer)</span>}</Label>
            <Input
              id="uf-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required={!isEdit}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Rôle</Label>
              <Select value={role} onValueChange={(v) => setRole(v as Role)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">Utilisateur</SelectItem>
                  <SelectItem value="admin">Administrateur</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end justify-between rounded-lg border border-border px-3 py-1.5">
              <Label htmlFor="uf-active" className="font-normal">Compte actif</Label>
              <Switch id="uf-active" checked={isActive} onCheckedChange={setIsActive} />
            </div>
          </div>

          <div className="space-y-2 rounded-lg border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Permissions</p>
            <PermissionRow label="Synchroniser les catalogues" checked={canSync} onChange={setCanSync} />
            <PermissionRow label="Supprimer des catalogues" checked={canDelete} onChange={setCanDelete} />
            <PermissionRow label="Rafraîchir les catalogues" checked={canRefresh} onChange={setCanRefresh} />
          </div>

          <div className="space-y-2 rounded-lg border border-border p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quota de synchronisation</p>
              <Switch checked={quota.enabled} onCheckedChange={(v) => setQuota({ ...quota, enabled: v })} />
            </div>
            {quota.enabled && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="space-y-1.5">
                  <Label htmlFor="uf-quota-max" className="text-xs">Maximum</Label>
                  <Input
                    id="uf-quota-max"
                    type="number"
                    min={1}
                    value={quota.max_syncs}
                    onChange={(e) => setQuota({ ...quota, max_syncs: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Période</Label>
                  <Select value={quota.period} onValueChange={(v) => setQuota({ ...quota, period: v as QuotaConfig['period'] })}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="day">Par jour</SelectItem>
                      <SelectItem value="month">Par mois</SelectItem>
                      <SelectItem value="year">Par an</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Annuler
          </Button>
          <Button type="submit" form="user-form" disabled={isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            {isEdit ? 'Enregistrer' : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PermissionRow({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between">
      <Label className="font-normal">{label}</Label>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  )
}
