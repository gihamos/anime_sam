import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useCreateCustomer, type CreatedCustomer } from '@/hooks/useAdminCustomers'
import { getApiError } from '@/api/client'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface CustomerCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CustomerCreateDialog({ open, onOpenChange }: CustomerCreateDialogProps) {
  const createCustomer = useCreateCustomer()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [created, setCreated] = useState<CreatedCustomer | null>(null)

  function reset() {
    setUsername('')
    setEmail('')
    setPassword('')
    setDateOfBirth('')
    setCreated(null)
  }

  async function handleSubmit() {
    if (!username.trim()) {
      toast.error("Nom d'utilisateur requis")
      return
    }
    if (!dateOfBirth) {
      toast.error('Date de naissance requise')
      return
    }
    try {
      const result = await createCustomer.mutateAsync({ username: username.trim(), email, password, dateOfBirth })
      if (result.generated_password) {
        setCreated(result)
      } else {
        toast.success('Client créé')
        reset()
        onOpenChange(false)
      }
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  function handleClose(v: boolean) {
    if (!v) reset()
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ajouter un client</DialogTitle>
          <DialogDescription>
            Crée un compte directement, sans passer par l'inscription publique — utile pour attribuer
            ensuite un abonnement à un client qui ne s'est pas encore inscrit lui-même.
          </DialogDescription>
        </DialogHeader>

        {created ? (
          <div className="space-y-4">
            <Alert>
              <AlertTitle>Compte créé</AlertTitle>
              <AlertDescription>
                <p>Nom d'utilisateur : <span className="font-mono">{created.username}</span></p>
                <p>Mot de passe généré : <span className="font-mono">{created.generated_password}</span></p>
                <p className="mt-1 text-xs">Notez-le maintenant — il ne sera plus jamais affiché.</p>
              </AlertDescription>
            </Alert>
            <DialogFooter>
              <Button onClick={() => { reset(); onOpenChange(false) }}>Fermer</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="create-username">Nom d'utilisateur</Label>
                <Input id="create-username" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="create-email">E-mail (optionnel)</Label>
                <Input id="create-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="create-dob">Date de naissance</Label>
                <Input
                  id="create-dob"
                  type="date"
                  value={dateOfBirth}
                  onChange={(e) => setDateOfBirth(e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                />
                <p className="text-xs text-muted-foreground">Sert à appliquer les restrictions de contenu liées à l'âge.</p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="create-password">Mot de passe (optionnel)</Label>
                <Input
                  id="create-password"
                  type="password"
                  placeholder="Laisser vide pour en générer un automatiquement"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
              <Button onClick={handleSubmit} disabled={createCustomer.isPending}>
                {createCustomer.isPending && <Loader2 className="size-4 animate-spin" />}
                Créer
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
