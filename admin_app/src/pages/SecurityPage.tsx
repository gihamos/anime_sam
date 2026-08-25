import { useState } from 'react'
import { toast } from 'sonner'
import { Lock, LockOpen, ShieldBan, Trash2, Unlock } from 'lucide-react'
import { useAddIpBan, useIpBans, useRemoveIpBan, useSecurityState, useSetApiLock } from '@/hooks/useSecurity'
import { getApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Alert, AlertDescription } from '@/components/ui/alert'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export function SecurityPage() {
  const { data: state, isLoading } = useSecurityState()
  const setLock = useSetApiLock()
  const { data: bans = [], isLoading: bansLoading } = useIpBans()
  const addBan = useAddIpBan()
  const removeBan = useRemoveIpBan()

  const [reason, setReason] = useState('')
  const [banIp, setBanIp] = useState('')
  const [banReason, setBanReason] = useState('')

  async function handleToggleLock() {
    try {
      await setLock.mutateAsync({ locked: !state?.locked, reason })
      toast.success(state?.locked ? "API déverrouillée" : 'API verrouillée')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleAddBan() {
    if (!banIp.trim()) return
    try {
      await addBan.mutateAsync({ ip: banIp.trim(), reason: banReason })
      toast.success(`IP ${banIp} bannie`)
      setBanIp('')
      setBanReason('')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  async function handleRemoveBan(ip: string) {
    try {
      await removeBan.mutateAsync(ip)
      toast.success('Ban levé')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Sécurité</h1>
        <p className="text-sm text-muted-foreground">Verrouillage de l'API et adresses IP bannies.</p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center gap-2 space-y-0">
          <CardTitle className="flex items-center gap-2 text-base">
            <Lock className="size-4" />
            Verrouillage de l'API
          </CardTitle>
          {isLoading ? (
            <Skeleton className="h-5 w-16" />
          ) : (
            <Badge className={state?.locked ? '' : 'bg-success text-success-foreground'} variant={state?.locked ? 'destructive' : 'default'}>
              {state?.locked ? 'Verrouillée' : 'Ouverte'}
            </Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Quand l'API est verrouillée, tous les utilisateurs non-administrateurs reçoivent une erreur 503.
            Les administrateurs et la route de connexion restent accessibles.
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="lock-reason">Message affiché aux utilisateurs bloqués</Label>
            <Input
              id="lock-reason"
              value={reason || state?.reason || ''}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Maintenance en cours, revenez plus tard..."
            />
          </div>
          <Button variant={state?.locked ? 'secondary' : 'destructive'} onClick={handleToggleLock} disabled={setLock.isPending}>
            {state?.locked ? <Unlock className="size-4" /> : <LockOpen className="size-4" />}
            {state?.locked ? "Déverrouiller l'API" : "Verrouiller l'API"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldBan className="size-4" />
            Adresses IP bannies
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Input value={banIp} onChange={(e) => setBanIp(e.target.value)} placeholder="192.168.1.100" className="flex-1 min-w-36" />
            <Input value={banReason} onChange={(e) => setBanReason(e.target.value)} placeholder="Raison (optionnel)" className="flex-[2] min-w-40" />
            <Button variant="destructive" onClick={handleAddBan} disabled={!banIp.trim() || addBan.isPending}>
              Bannir
            </Button>
          </div>

          {banIp && !/^(\d{1,3}\.){3}\d{1,3}$/.test(banIp) && (
            <Alert variant="destructive">
              <AlertDescription>Format IP invalide.</AlertDescription>
            </Alert>
          )}

          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IP</TableHead>
                  <TableHead>Raison</TableHead>
                  <TableHead>Banni le</TableHead>
                  <TableHead>Par</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {bansLoading &&
                  Array.from({ length: 2 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={5}><Skeleton className="h-6 w-full" /></TableCell>
                    </TableRow>
                  ))}
                {!bansLoading && bans.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">Aucune IP bannie.</TableCell>
                  </TableRow>
                )}
                {bans.map((ban) => (
                  <TableRow key={ban.ip}>
                    <TableCell className="font-mono text-sm">{ban.ip}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ban.reason || '—'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(ban.banned_at)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ban.banned_by}</TableCell>
                    <TableCell>
                      <Button size="icon-sm" variant="ghost" onClick={() => handleRemoveBan(ban.ip)}>
                        <Trash2 className="size-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
