import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { getApiError } from '@/api/client'
import { useCatalogues } from '@/hooks/useCatalogues'
import { useCreateSchedule, useUpdateSchedule } from '@/hooks/useSchedules'
import type { Schedule, ScheduleFrequency } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

interface ScheduleFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  schedule: Schedule | null
}

export function ScheduleFormDialog({ open, onOpenChange, schedule }: ScheduleFormDialogProps) {
  const isEdit = !!schedule
  // La programmation ré-exécute le scraper anime-sama.to — non applicable aux catalogues
  // TMDB/Vidzy, qui n'ont pas de mécanisme de resynchronisation périodique (voir backend).
  const { data: allCatalogues = [] } = useCatalogues()
  const catalogues = allCatalogues.filter((c) => c.source !== 'tmdb-vidzy')
  const createSchedule = useCreateSchedule()
  const updateSchedule = useUpdateSchedule()
  const isPending = createSchedule.isPending || updateSchedule.isPending

  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [frequency, setFrequency] = useState<ScheduleFrequency>('weekly')
  const [hour, setHour] = useState(2)
  const [minute, setMinute] = useState(0)
  const [dayOfWeek, setDayOfWeek] = useState(0)
  const [dayOfMonth, setDayOfMonth] = useState(1)
  const [intervalDays, setIntervalDays] = useState(7)
  const [active, setActive] = useState(true)

  useEffect(() => {
    if (!open) return
    if (schedule) {
      setSlug(schedule.slug)
      setDescription(schedule.description ?? '')
      setFrequency(schedule.frequency)
      setHour(schedule.hour)
      setMinute(schedule.minute)
      setDayOfWeek(schedule.day_of_week ?? 0)
      setDayOfMonth(schedule.day_of_month ?? 1)
      setIntervalDays(schedule.interval_days ?? 7)
      setActive(schedule.active)
    } else {
      setSlug('')
      setDescription('')
      setFrequency('weekly')
      setHour(2)
      setMinute(0)
      setDayOfWeek(0)
      setDayOfMonth(1)
      setIntervalDays(7)
      setActive(true)
    }
  }, [open, schedule])

  async function handleSave() {
    if (!slug) {
      toast.error('Sélectionnez un catalogue')
      return
    }
    const body = {
      frequency,
      hour,
      minute,
      day_of_week: ['weekly', 'biweekly'].includes(frequency) ? dayOfWeek : null,
      day_of_month: frequency === 'monthly' ? dayOfMonth : null,
      interval_days: frequency === 'custom' ? intervalDays : null,
      description: description || undefined,
      active,
    }
    try {
      if (isEdit && schedule) {
        await updateSchedule.mutateAsync({ id: schedule.id, body })
        toast.success('Programmation mise à jour')
      } else {
        await createSchedule.mutateAsync({ slug, ...body })
        toast.success('Programmation créée')
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
          <DialogTitle>{isEdit ? 'Modifier la programmation' : 'Nouvelle programmation'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Catalogue</Label>
            <Select value={slug} onValueChange={(v) => setSlug(v ?? '')} disabled={isEdit}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Sélectionner un catalogue..." />
              </SelectTrigger>
              <SelectContent>
                {catalogues.map((c) => (
                  <SelectItem key={c.slug} value={c.slug}>{c.nom}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="sf-desc">Description</Label>
            <Input id="sf-desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optionnel" />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Fréquence</Label>
              <Select value={frequency} onValueChange={(v) => setFrequency(v as ScheduleFrequency)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Quotidien</SelectItem>
                  <SelectItem value="weekly">Hebdomadaire</SelectItem>
                  <SelectItem value="biweekly">Bi-hebdomadaire</SelectItem>
                  <SelectItem value="monthly">Mensuel</SelectItem>
                  <SelectItem value="custom">Personnalisé (N jours)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Heure (UTC)</Label>
              <div className="flex items-center gap-1.5">
                <Input type="number" min={0} max={23} value={hour} onChange={(e) => setHour(Number(e.target.value))} />
                <span className="text-muted-foreground">h</span>
                <Input type="number" min={0} max={59} value={minute} onChange={(e) => setMinute(Number(e.target.value))} />
              </div>
            </div>
          </div>

          {['weekly', 'biweekly'].includes(frequency) && (
            <div className="space-y-1.5">
              <Label>Jour de la semaine</Label>
              <Select value={String(dayOfWeek)} onValueChange={(v) => setDayOfWeek(Number(v))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DAYS.map((d, i) => (
                    <SelectItem key={d} value={String(i)}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {frequency === 'monthly' && (
            <div className="space-y-1.5">
              <Label>Jour du mois (1-28)</Label>
              <Input type="number" min={1} max={28} value={dayOfMonth} onChange={(e) => setDayOfMonth(Number(e.target.value))} />
            </div>
          )}

          {frequency === 'custom' && (
            <div className="space-y-1.5">
              <Label>Tous les N jours</Label>
              <Input type="number" min={1} value={intervalDays} onChange={(e) => setIntervalDays(Number(e.target.value))} />
            </div>
          )}

          <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
            <Label className="font-normal">Programmation active</Label>
            <Switch checked={active} onCheckedChange={setActive} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Annuler
          </Button>
          <Button onClick={handleSave} disabled={isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
