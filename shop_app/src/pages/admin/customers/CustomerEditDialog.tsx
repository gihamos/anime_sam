import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useUpdateCustomer } from '@/hooks/useAdminCustomers'
import { getApiError } from '@/api/client'
import type { Customer } from '@/api/types'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface CustomerEditDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  customer: Customer | null
}

export function CustomerEditDialog({ open, onOpenChange, customer }: CustomerEditDialogProps) {
  const updateCustomer = useUpdateCustomer()
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [dateOfBirth, setDateOfBirth] = useState('')

  useEffect(() => {
    setEmail(customer?.email ?? '')
    setNewPassword('')
    setDateOfBirth(customer?.date_of_birth?.slice(0, 10) ?? '')
  }, [customer, open])

  async function handleSubmit() {
    if (!customer) return
    if (newPassword && newPassword.length < 8) {
      toast.error('Le mot de passe doit contenir au moins 8 caractères')
      return
    }
    try {
      await updateCustomer.mutateAsync({ username: customer.username, email, newPassword, dateOfBirth })
      toast.success('Client mis à jour')
      onOpenChange(false)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modifier {customer?.username}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="edit-email">E-mail</Label>
            <Input id="edit-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-dob">Date de naissance</Label>
            <Input
              id="edit-dob"
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              max={new Date().toISOString().slice(0, 10)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-password">Nouveau mot de passe</Label>
            <Input
              id="edit-password"
              type="password"
              placeholder="Laisser vide pour ne pas changer"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
          <Button onClick={handleSubmit} disabled={updateCustomer.isPending}>
            {updateCustomer.isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
