import { Check, Copy, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface SecretDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  clientId: string | null
  clientSecret: string | null
}

export function SecretDialog({ open, onOpenChange, clientId, clientSecret }: SecretDialogProps) {
  const [copied, setCopied] = useState<'id' | 'secret' | null>(null)

  function copy(value: string, kind: 'id' | 'secret') {
    navigator.clipboard.writeText(value)
    setCopied(kind)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Secret généré</DialogTitle>
          <DialogDescription>Utilisez ces identifiants avec POST /auth/client-token.</DialogDescription>
        </DialogHeader>

        <Alert>
          <TriangleAlert className="size-4" />
          <AlertDescription>Copiez ce secret maintenant — il ne sera plus jamais affiché après la fermeture de cette fenêtre.</AlertDescription>
        </Alert>

        <div className="space-y-2">
          <SecretField label="Client ID" value={clientId ?? ''} copied={copied === 'id'} onCopy={() => copy(clientId ?? '', 'id')} />
          <SecretField label="Client Secret" value={clientSecret ?? ''} copied={copied === 'secret'} onCopy={() => copy(clientSecret ?? '', 'secret')} />
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Fermer</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SecretField({ label, value, copied, onCopy }: { label: string; value: string; copied: boolean; onCopy: () => void }) {
  return (
    <div className="space-y-1 rounded-lg border border-border p-2.5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex items-center gap-2">
        <code className="flex-1 truncate text-xs">{value}</code>
        <Button size="icon-sm" variant="ghost" onClick={onCopy}>
          {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
        </Button>
      </div>
    </div>
  )
}
