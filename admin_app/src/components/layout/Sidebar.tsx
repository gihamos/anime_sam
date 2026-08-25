import { NavLink } from 'react-router-dom'
import {
  Users,
  Library,
  Search,
  UsersRound,
  Blocks,
  CalendarClock,
  Download,
  ShieldCheck,
  Activity,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

export const NAV_ITEMS = [
  { to: '/catalogues', label: 'Catalogues', icon: Library },
  { to: '/recherche', label: 'Recherche', icon: Search },
  { to: '/utilisateurs', label: 'Utilisateurs', icon: Users },
  { to: '/groupes', label: 'Groupes', icon: UsersRound },
  { to: '/applications', label: 'Applications', icon: Blocks },
  { to: '/planification', label: 'Planification', icon: CalendarClock },
  { to: '/telechargements', label: 'Téléchargements', icon: Download },
  { to: '/securite', label: 'Sécurité', icon: ShieldCheck },
  { to: '/connexions', label: 'Connexions', icon: Activity },
]

interface SidebarContentProps {
  onNavigate?: () => void
}

export function SidebarContent({ onNavigate }: SidebarContentProps) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggle)

  return (
    <div className="flex h-full flex-col">
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
            onClick={onNavigate}
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
      </nav>
      <Separator />
      <div className="space-y-2 p-3">
        {user && <p className="truncate px-1 text-xs text-muted-foreground">{user.username}</p>}
        <Button variant="secondary" size="sm" className="w-full justify-start gap-2" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          {theme === 'dark' ? 'Thème clair' : 'Thème sombre'}
        </Button>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground" onClick={logout}>
          <LogOut className="size-4" />
          Déconnexion
        </Button>
      </div>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="hidden h-full w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex">
      <SidebarContent />
    </aside>
  )
}
