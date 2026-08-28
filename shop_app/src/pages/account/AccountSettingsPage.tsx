import { type FormEvent, useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useUpdateAccount, useChangePassword } from '@/hooks/useAccountSettings'
import { getApiError } from '@/api/client'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function AccountSettingsPage() {
  const customer = useAuthStore((s) => s.customer)
  const updateAccount = useUpdateAccount()
  const changePassword = useChangePassword()

  const [email, setEmail] = useState(customer?.email ?? '')
  const [dateOfBirth, setDateOfBirth] = useState(customer?.date_of_birth?.slice(0, 10) ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  async function handleEmailSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await updateAccount.mutateAsync({ email, dateOfBirth })
      toast.success('Informations mises à jour')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault()
    if (newPassword.length < 8) {
      toast.error('Le nouveau mot de passe doit contenir au moins 8 caractères')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Les deux mots de passe ne correspondent pas')
      return
    }
    try {
      await changePassword.mutateAsync({ currentPassword, newPassword })
      toast.success('Mot de passe mis à jour')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Paramètres du compte</h1>
        <p className="text-sm text-muted-foreground">Gérez vos informations de connexion.</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Informations</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleEmailSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">Nom d'utilisateur</Label>
              <Input id="username" value={customer?.username ?? ''} disabled />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="date-of-birth">Date de naissance</Label>
              <Input
                id="date-of-birth"
                type="date"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
                max={new Date().toISOString().slice(0, 10)}
              />
              <p className="text-xs text-muted-foreground">Sert à appliquer les restrictions de contenu liées à l'âge.</p>
            </div>
            <Button type="submit" disabled={updateAccount.isPending}>
              {updateAccount.isPending && <Loader2 className="size-4 animate-spin" />}
              Enregistrer
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Mot de passe</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current-password">Mot de passe actuel</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-password">Nouveau mot de passe</Label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">Confirmer le nouveau mot de passe</Label>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={changePassword.isPending}>
              {changePassword.isPending && <Loader2 className="size-4 animate-spin" />}
              Changer le mot de passe
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
