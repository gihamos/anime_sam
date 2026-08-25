import { NavLink } from 'react-router-dom'
import {
  User,
  Receipt,
  LifeBuoy,
  LayoutGrid,
  Users,
  Ticket,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'

const CUSTOMER_NAV = [
  { to: '/compte', label: 'Mon compte', icon: User },
  { to: '/compte/facturation', label: 'Facturation', icon: Receipt },
  { to: '/compte/tickets', label: 'Support', icon: LifeBuoy },
]

const ADMIN_NAV = [
  { to: '/admin/offres', label: 'Offres', icon: LayoutGrid },
  { to: '/admin/abonnements', label: 'Abonnements', icon: Users },
  { to: '/admin/tickets', label: 'Tickets', icon: Ticket },
]

interface SidebarContentProps {
  onNavigate?: () => void
}

export function SidebarContent({ onNavigate }: SidebarContentProps) {
  const customer = useAuthStore((s) => s.customer)
  const logout = useAuthStore((s) => s.logout)
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggle)
  const isAdmin = customer?.role === 'admin'
  const items = isAdmin ? ADMIN_NAV : CUSTOMER_NAV

  return (
    <div className="flex h-full flex-col">
      <div className="px-4 py-4">
        <p className="text-sm font-semibold text-primary">Anime Sama</p>
        <p className="text-xs text-muted-foreground">{isAdmin ? 'Administration boutique' : 'Mon espace'}</p>
      </div>
      <Separator />
      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/compte'}
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
        {customer && (
          <div className="flex items-center gap-2 px-1">
            <p className="truncate text-xs text-muted-foreground">{customer.username}</p>
            {isAdmin && <Badge variant="secondary" className="text-[10px]">Admin</Badge>}
          </div>
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
