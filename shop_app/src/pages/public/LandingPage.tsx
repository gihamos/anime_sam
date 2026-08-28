import { Link } from 'react-router-dom'
import { ArrowRight, Clapperboard, Download, Play, ShieldCheck, Smartphone, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { TrendingRow } from './landing/TrendingRow'

const HERO_BACKDROP = 'https://image.tmdb.org/t/p/w1280/qpin8cASXEVtwhzNsprHYFiOAGk.jpg'

const FEATURES = [
  {
    icon: Play,
    title: 'Lecture immédiate',
    description: "Lancez un épisode ou un film en un clic, sur votre navigateur, votre TV ou vos applications Jellyfin préférées.",
  },
  {
    icon: Smartphone,
    title: 'Multi-appareils',
    description: 'Regardez sur plusieurs appareils à la fois selon votre palier, du canapé au trajet en transport.',
  },
  {
    icon: Download,
    title: 'Téléchargement hors ligne',
    description: 'Emportez vos épisodes préférés avec vous et regardez-les même sans connexion, sur les paliers concernés.',
  },
  {
    icon: ShieldCheck,
    title: 'Compte prêt en quelques minutes',
    description: "Votre accès s'active automatiquement après paiement, aucune configuration technique de votre côté.",
  },
]

const STEPS = [
  {
    number: '01',
    title: 'Choisissez votre offre',
    description: 'Anime seul, ou catalogue complet avec films et séries. Un palier pour chaque façon de regarder.',
  },
  {
    number: '02',
    title: 'Activez votre accès',
    description: 'Le paiement est sécurisé par PayPal et votre compte est créé automatiquement, sans attente.',
  },
  {
    number: '03',
    title: 'Regardez tout de suite',
    description: 'Connectez-vous depuis votre application Jellyfin favorite et plongez dans le catalogue.',
  },
]

export function LandingPage() {
  return (
    <div>
      <section className="relative isolate overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <img
            src={HERO_BACKDROP}
            alt=""
            className="size-full object-cover object-top opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/85 to-background/20" />
          <div className="absolute inset-0 bg-gradient-to-r from-background/70 via-transparent to-background/70" />
        </div>

        <div className="mx-auto max-w-4xl px-4 py-24 text-center sm:px-6 sm:py-32">
          <div className="mb-5 inline-flex animate-in fade-in slide-in-from-bottom-2 items-center gap-1.5 rounded-full border border-border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur-sm">
            <Sparkles className="size-3.5 text-primary" />
            Animes, films et séries réunis au même endroit
          </div>
          <h1 className="animate-in fade-in slide-in-from-bottom-4 text-4xl font-semibold tracking-tight text-balance sm:text-6xl" style={{ animationDuration: '600ms' }}>
            Votre plateforme de streaming, prête en quelques minutes
          </h1>
          <p className="mx-auto mt-5 max-w-xl animate-in fade-in slide-in-from-bottom-4 text-base text-muted-foreground sm:text-lg" style={{ animationDuration: '700ms' }}>
            Un abonnement, un accès Jellyfin qui vous appartient. Choisissez votre palier
            et commencez à regarder aujourd'hui.
          </p>
          <div className="mt-9 flex animate-in fade-in slide-in-from-bottom-4 flex-col items-center justify-center gap-3 sm:flex-row" style={{ animationDuration: '800ms' }}>
            <Button size="lg" className="gap-2" render={<Link to="/tarifs" />} nativeButton={false}>
              Voir les offres
              <ArrowRight className="size-4" />
            </Button>
            <Button size="lg" variant="outline" render={<Link to="/inscription" />} nativeButton={false}>
              Créer un compte gratuitement
            </Button>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Tendances du moment</h2>
          <Link to="/tarifs" className="text-sm text-primary hover:underline">Voir les offres</Link>
        </div>
        <TrendingRow />
      </section>

      <section className="border-y border-border bg-muted/40 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">Trois étapes, et c'est parti</h2>
            <p className="mt-2 text-muted-foreground">Aucune installation compliquée, aucun engagement caché.</p>
          </div>
          <div className="grid gap-8 sm:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.number} className="text-center sm:text-left">
                <span className="text-sm font-semibold text-primary">{step.number}</span>
                <h3 className="mt-2 text-base font-semibold">{step.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">Pensé pour regarder, pas pour configurer</h2>
          <p className="mt-2 text-muted-foreground">Tout ce qu'il faut pour profiter du catalogue confortablement.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title} className="transition-transform duration-200 hover:-translate-y-1 hover:shadow-md">
              <CardHeader>
                <div className="mb-2 flex size-9 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <Icon className="size-4" />
                </div>
                <h3 className="text-sm font-semibold">{title}</h3>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary to-primary/70 px-6 py-14 text-center sm:px-16">
          <Clapperboard className="mx-auto mb-4 size-8 text-primary-foreground/90" />
          <h2 className="text-2xl font-semibold text-primary-foreground sm:text-3xl">
            Prêt à regarder sans limites
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-primary-foreground/85 sm:text-base">
            Rejoignez la plateforme et accédez au catalogue complet dès aujourd'hui.
          </p>
          <Button
            size="lg"
            className="mt-7 gap-2 bg-white text-slate-900 hover:bg-white/90"
            render={<Link to="/tarifs" />}
            nativeButton={false}
          >
            Choisir mon offre
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>
    </div>
  )
}
