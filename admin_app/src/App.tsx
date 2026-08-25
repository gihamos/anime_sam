import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { CataloguesPage } from '@/pages/CataloguesPage'
import { RecherchePage } from '@/pages/RecherchePage'
import { UsersPage } from '@/pages/UsersPage'
import { GroupsPage } from '@/pages/GroupsPage'
import { ApplicationsPage } from '@/pages/ApplicationsPage'
import { PlanningPage } from '@/pages/PlanningPage'
import { DownloadsPage } from '@/pages/DownloadsPage'
import { SecurityPage } from '@/pages/SecurityPage'
import { ConnectionsPage } from '@/pages/ConnectionsPage'

function ProtectedShell() {
  const { isAuthenticated, ready } = useAuthStore()

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <AppShell />
}

function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedShell />}>
        <Route path="/" element={<Navigate to="/catalogues" replace />} />
        <Route path="/catalogues" element={<CataloguesPage />} />
        <Route path="/recherche" element={<RecherchePage />} />
        <Route path="/films-series" element={<Navigate to="/recherche" replace />} />
        <Route path="/utilisateurs" element={<UsersPage />} />
        <Route path="/groupes" element={<GroupsPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/planification" element={<PlanningPage />} />
        <Route path="/telechargements" element={<DownloadsPage />} />
        <Route path="/securite" element={<SecurityPage />} />
        <Route path="/connexions" element={<ConnectionsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
