export type CustomerRole = 'customer' | 'admin'

export interface Customer {
  username: string
  email: string | null
  role: CustomerRole
  is_active: boolean
  created_at: string | null
}

export interface Plan {
  id: string
  slug: string
  name: string
  description: string
  price: number
  currency: string
  billing_period: string
  jellyfin_library_names: string[]
  max_devices: number
  allow_downloads: boolean
  sort_order: number
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
  cancel_at_period_end: boolean
  current_period_end: string | null
  jellyfin_user_id: string | null
  jellyfin_username: string | null
  created_at: string
  updated_at: string
  activated_at: string | null
  cancelled_at: string | null
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
