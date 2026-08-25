import { Link } from 'react-router-dom'
import { PlayCircle, ShieldCheck, Smartphone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

const FEATURES = [
  {
    icon: PlayCircle,
    title: 'Streaming immédiat',
    description: "Accédez au catalogue directement depuis votre navigateur, votre TV ou vos applications Jellyfin préférées.",
  },
  {
    icon: Smartphone,
    title: 'Multi-appareils',
    description: 'Regardez sur plusieurs appareils selon le palier choisi, avec un nombre de sessions simultanées adapté.',
  },
  {
    icon: ShieldCheck,
    title: 'Compte géré pour vous',
    description: "Votre compte est activé automatiquement après paiement, sans configuration technique de votre côté.",
  },
]

export function LandingPage() {
  return (
    <div>
      <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Votre bibliothèque animés, films et séries, en streaming
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
          Un abonnement, un accès. Choisissez le palier qui correspond à votre usage et
          commencez à regarder en quelques minutes.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Button size="lg" render={<Link to="/tarifs" />} nativeButton={false}>
            Voir les tarifs
          </Button>
          <Button size="lg" variant="outline" render={<Link to="/inscription" />} nativeButton={false}>
            Créer un compte
          </Button>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-20 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title}>
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <Icon className="size-4" />
                </div>
                <h2 className="text-sm font-semibold">{title}</h2>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}
