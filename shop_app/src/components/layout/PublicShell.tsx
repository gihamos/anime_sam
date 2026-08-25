import { Link, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'

export function PublicShell() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const customer = useAuthStore((s) => s.customer)

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="text-sm font-semibold text-primary">
            Anime Sama
          </Link>
          <nav className="flex items-center gap-2">
            <Button variant="ghost" size="sm" render={<Link to="/tarifs" />} nativeButton={false}>
              Tarifs
            </Button>
            {isAuthenticated ? (
              <Button size="sm" render={<Link to={customer?.role === 'admin' ? '/admin/offres' : '/compte'} />} nativeButton={false}>
                Mon compte
              </Button>
            ) : (
              <>
                <Button variant="ghost" size="sm" render={<Link to="/connexion" />} nativeButton={false}>
                  Connexion
                </Button>
                <Button size="sm" render={<Link to="/inscription" />} nativeButton={false}>
                  S'inscrire
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-muted-foreground sm:px-6">
          © {new Date().getFullYear()} Anime Sama — Accès au serveur Jellyfin sur abonnement.
        </div>
      </footer>
    </div>
  )
}
