import { NavLink } from 'react-router-dom'
import { Users, Library, Clapperboard, ExternalLink, LogOut, Sun, Moon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

const NAV_ITEMS = [
  { to: '/catalogues', label: 'Catalogues', icon: Library },
  { to: '/films-series', label: 'Films et séries', icon: Clapperboard },
  { to: '/utilisateurs', label: 'Utilisateurs', icon: Users },
]

export function Sidebar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggle)

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="px-4 py-4">
        <p className="text-sm font-semibold text-primary">Anime Sama</p>
        <p className="text-xs text-muted-foreground">Administration</p>
      </div>
      <Separator />
      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              )
            }
          >
            <Icon className="size-4" strokeWidth={2} />
            {label}
          </NavLink>
        ))}

        <Separator className="my-2" />

        <a
          href="/legacy/"
          className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <ExternalLink className="size-4" strokeWidth={2} />
          Interface classique
        </a>
      </nav>
      <Separator />
      <div className="space-y-2 p-3">
        {user && (
          <p className="truncate px-1 text-xs text-muted-foreground">{user.username}</p>
        )}
        <Button variant="secondary" size="sm" className="w-full justify-start gap-2" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          {theme === 'dark' ? 'Thème clair' : 'Thème sombre'}
        </Button>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground" onClick={logout}>
          <LogOut className="size-4" />
          Déconnexion
        </Button>
      </div>
    </aside>
  )
}
