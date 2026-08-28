export type CustomerRole = 'customer' | 'admin'

export interface Customer {
  username: string
  email: string | null
  role: CustomerRole
  is_active: boolean
  date_of_birth: string | null
  created_at: string | null
}

export interface Plan {
  id: string
  slug: string
  name: string
  description: string
  price: number
  currency: string
  duration_days: number
  jellyfin_library_names: string[]
  max_devices: number
  allow_downloads: boolean
  sort_order: number
  discount_type: DiscountType | null
  discount_value: number | null
  discount_expires_at: string | null
  discounted_price: number | null
  max_parental_rating: number | null
}

export interface PlanAdmin extends Plan {
  is_active: boolean
  jellyfin_library_folder_ids: string[]
  provider_refs: Record<string, Record<string, string>>
  created_at: string
  updated_at: string
}

export type SubscriptionStatus = 'pending' | 'active' | 'past_due' | 'suspended' | 'cancelled' | 'expired'

export interface SubscriptionDetail {
  id: string
  plan_id: string
  plan_name: string | null
  status: SubscriptionStatus
  auto_renew: boolean
  cancel_at_period_end: boolean
  current_period_end: string | null
  jellyfin_username: string | null
  jellyfin_initial_password_pending: string | null
  created_at: string | null
  activated_at: string | null
}

export interface SubscriptionAdmin {
  id: string
  username: string
  plan_id: string
  provider: string
  provider_subscription_id: string | null
  status: SubscriptionStatus
  auto_renew: boolean
  cancel_at_period_end: boolean
  current_period_end: string | null
  jellyfin_user_id: string | null
  jellyfin_username: string | null
  created_at: string
  updated_at: string
  activated_at: string | null
  cancelled_at: string | null
  jellyfin_initial_password_pending?: string | null
}

export interface Payment {
  id: string
  plan_id: string
  amount: number
  currency: string
  provider: string
  status: string
  paid_at: string | null
}

export type TicketStatus = 'open' | 'pending' | 'closed'

export interface TicketMessage {
  author_role: 'customer' | 'admin'
  author_username: string
  body: string
  created_at: string
}

export interface Ticket {
  id: string
  username: string
  subject: string
  status: TicketStatus
  messages: TicketMessage[]
  created_at: string
  updated_at: string
}

export interface LibraryFolder {
  id: string
  name: string
  type: string | null
}

export type DiscountType = 'percent' | 'fixed'

export interface Promotion {
  id: string
  code: string
  description: string
  discount_type: DiscountType
  discount_value: number
  applicable_plan_ids: string[]
  max_uses: number | null
  used_count: number
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export interface PromoPreview {
  code: string
  original_price: number
  discounted_price: number
  currency: string
}

export interface DailyRevenuePoint {
  date: string
  amount: number
  count: number
}

export interface PlanPopularity {
  plan_id: string
  plan_name: string
  count: number
}

export interface DashboardStats {
  total_customers: number
  new_customers_this_month: number
  active_subscriptions: number
  subscriptions_by_status: Record<string, number>
  total_revenue: number
  month_revenue: number
  daily_revenue: DailyRevenuePoint[]
  plan_popularity: PlanPopularity[]
}
