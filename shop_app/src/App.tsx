import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { PublicShell } from '@/components/layout/PublicShell'
import { AccountShell } from '@/components/layout/AccountShell'
import { LandingPage } from '@/pages/public/LandingPage'
import { PricingPage } from '@/pages/public/PricingPage'
import { LoginPage } from '@/pages/public/LoginPage'
import { RegisterPage } from '@/pages/public/RegisterPage'
import { AccountOverviewPage } from '@/pages/account/AccountOverviewPage'
import { BillingHistoryPage } from '@/pages/account/BillingHistoryPage'
import { PlanManagementPage } from '@/pages/account/PlanManagementPage'
import { TicketsPage } from '@/pages/account/TicketsPage'
import { TicketDetailPage } from '@/pages/account/TicketDetailPage'
import { CheckoutReturnPage } from '@/pages/account/CheckoutReturnPage'
import { CheckoutCancelPage } from '@/pages/account/CheckoutCancelPage'
import { AccountSettingsPage } from '@/pages/account/AccountSettingsPage'
import { PlansAdminPage } from '@/pages/admin/PlansAdminPage'
import { SubscriptionsAdminPage } from '@/pages/admin/SubscriptionsAdminPage'
import { CustomersAdminPage } from '@/pages/admin/CustomersAdminPage'
import { TicketsAdminPage } from '@/pages/admin/TicketsAdminPage'
import { StatsAdminPage } from '@/pages/admin/StatsAdminPage'
import { PromotionsAdminPage } from '@/pages/admin/PromotionsAdminPage'
import { SyncAdminPage } from '@/pages/admin/SyncAdminPage'

function LoadingScreen() {
  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  )
}

function ProtectedShell() {
  const { isAuthenticated, ready } = useAuthStore()

  if (!ready) return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/connexion" replace />
  return <AccountShell />
}

function AdminOnly() {
  const { customer, ready } = useAuthStore()

  if (!ready) return <LoadingScreen />
  if (customer?.role !== 'admin') return <Navigate to="/compte" replace />
  return <AccountShell />
}

function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <Routes>
      <Route element={<PublicShell />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/tarifs" element={<PricingPage />} />
        <Route path="/connexion" element={<LoginPage />} />
        <Route path="/inscription" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedShell />}>
        <Route path="/compte" element={<AccountOverviewPage />} />
        <Route path="/compte/facturation" element={<BillingHistoryPage />} />
        <Route path="/compte/abonnement" element={<PlanManagementPage />} />
        <Route path="/compte/tickets" element={<TicketsPage />} />
        <Route path="/compte/tickets/:ticketId" element={<TicketDetailPage />} />
        <Route path="/compte/paiement/retour" element={<CheckoutReturnPage />} />
        <Route path="/compte/paiement/annule" element={<CheckoutCancelPage />} />
        <Route path="/compte/parametres" element={<AccountSettingsPage />} />
      </Route>

      <Route element={<AdminOnly />}>
        <Route path="/admin/statistiques" element={<StatsAdminPage />} />
        <Route path="/admin/offres" element={<PlansAdminPage />} />
        <Route path="/admin/promotions" element={<PromotionsAdminPage />} />
        <Route path="/admin/abonnements" element={<SubscriptionsAdminPage />} />
        <Route path="/admin/clients" element={<CustomersAdminPage />} />
        <Route path="/admin/tickets" element={<TicketsAdminPage />} />
        <Route path="/admin/synchronisation" element={<SyncAdminPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
