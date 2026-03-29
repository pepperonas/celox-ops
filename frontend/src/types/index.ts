export interface Customer {
  id: string
  name: string
  email: string
  phone: string
  company: string
  address: string
  website: string
  token_tracker_url: string
  notes: string
  created_at: string
  updated_at: string
}

export interface TokenTrackerData {
  label: string
  period: { from: string | null; to: string | null }
  summary: {
    total_input_tokens: number
    total_output_tokens: number
    total_cache_read_tokens: number
    total_messages: number
    total_sessions: number
    total_cost: number
    lines_added: number
    lines_removed: number
    lines_written: number
    total_duration_min: number
    total_active_min: number
    first_activity: string | null
    last_activity: string | null
    models_used: { name: string; messages: number; cost: number }[]
    tools: { name: string; calls: number }[]
  }
  daily: {
    date: string
    input_tokens: number
    output_tokens: number
    cache_read_tokens: number
    messages: number
    cost: number
    lines_added: number
    lines_removed: number
    lines_written: number
  }[]
  sessions: {
    start: string
    end: string
    messages: number
    input_tokens: number
    output_tokens: number
    cost: number
    duration_min: number
    active_min: number
    model: string
    lines_added: number
    lines_removed: number
    lines_written: number
  }[]
}

export interface CustomerDetail extends Customer {
  orders_count: number
  contracts_count: number
  invoices_count: number
}

export interface CustomerCreate {
  name: string
  email?: string
  phone?: string
  company?: string
  address?: string
  website?: string
  token_tracker_url?: string
  notes?: string
}

export interface QuickInvoiceCreate {
  customer_id: string
  beschreibung: string
  menge: number
  einheit: string
  einzelpreis: number
  notes?: string
}

export interface CustomerUpdate extends Partial<CustomerCreate> {}

export type OrderStatus = 'angebot' | 'beauftragt' | 'in_arbeit' | 'abgeschlossen' | 'storniert'

export interface Order {
  id: string
  customer_id: string
  customer_name?: string
  title: string
  description: string
  status: OrderStatus
  amount: number
  hourly_rate: number
  start_date: string
  end_date: string
  positions: InvoicePosition[] | null
  quote_pdf_path: string | null
  valid_until: string | null
  created_at: string
  updated_at: string
}

export interface OrderCreate {
  customer_id: string
  title: string
  description?: string
  status?: OrderStatus
  amount?: number
  hourly_rate?: number
  start_date?: string
  end_date?: string
  positions?: InvoicePosition[] | null
  valid_until?: string
}

export interface OrderUpdate extends Partial<OrderCreate> {}

export type ContractType = 'hosting' | 'wartung' | 'support' | 'sonstige'
export type ContractStatus = 'aktiv' | 'gekuendigt' | 'ausgelaufen'
export type BillingCycle = 'monatlich' | 'quartalsweise' | 'halbjaehrlich' | 'jaehrlich'

export interface Contract {
  id: string
  customer_id: string
  customer_name?: string
  title: string
  type: ContractType
  description: string
  monthly_amount: number
  billing_cycle: string
  start_date: string
  end_date: string
  auto_renew: boolean
  notice_period_days: number
  last_invoiced_date: string | null
  status: ContractStatus
  created_at: string
  updated_at: string
}

export interface ContractCreate {
  customer_id: string
  title: string
  description?: string
  type: ContractType
  status?: ContractStatus
  monthly_amount?: number
  billing_cycle?: string
  start_date?: string
  end_date?: string
  auto_renew?: boolean
  notice_period_days?: number
}

export interface ContractUpdate extends Partial<ContractCreate> {}

export interface Task {
  type: string
  priority: 'critical' | 'warning' | 'info'
  title: string
  subtitle: string
  detail: string
  link: string
  date: string
}

export type InvoiceStatus = 'entwurf' | 'gestellt' | 'bezahlt' | 'ueberfaellig' | 'storniert'

export interface InvoicePosition {
  position: number
  beschreibung: string
  menge: number
  einheit: string
  einzelpreis: number
  gesamt: number
}

export interface Invoice {
  id: string
  customer_id: string
  customer_name?: string
  order_id: string | null
  contract_id: string | null
  invoice_number: string
  title: string
  status: InvoiceStatus
  positions: InvoicePosition[]
  subtotal: number
  tax_rate: number
  tax_amount: number
  total: number
  invoice_date: string
  due_date: string
  pdf_path: string | null
  notes: string
  token_usage_from: string | null
  token_usage_to: string | null
  reminder_level: number
  reminder_sent_at: string | null
  reminder_pdf_path: string | null
  amount_paid: number
  is_credit_note: boolean
  credit_note_for: string | null
  created_at: string
  updated_at: string
}

export interface InvoiceCreate {
  customer_id: string
  order_id?: string | null
  contract_id?: string | null
  title: string
  positions: InvoicePosition[]
  tax_rate?: number
  invoice_date?: string
  due_date?: string
  notes?: string
  token_usage_from?: string | null
  token_usage_to?: string | null
}

export interface InvoiceUpdate extends Partial<InvoiceCreate> {}

export type LeadStatus = 'neu' | 'kontaktiert' | 'interessiert' | 'abgelehnt'

export interface Lead {
  id: string
  url: string
  name: string
  company: string
  email: string
  phone: string
  notes: string
  status: LeadStatus
  created_at: string
  updated_at: string
}

export interface LeadCreate {
  url: string
  name?: string
  company?: string
  email?: string
  phone?: string
  notes?: string
  status?: LeadStatus
}

export interface LeadUpdate extends Partial<LeadCreate> {}

export interface DashboardStats {
  revenue_month: number
  revenue_year: number
  open_invoices_count: number
  open_invoices_sum: number
  overdue_invoices_count: number
  overdue_invoices_sum: number
  active_contracts_count: number
  active_contracts_monthly_sum: number
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface TimeEntry {
  id: string
  customer_id: string
  customer_name?: string
  description: string
  date: string
  hours: number
  hourly_rate: number | null
  notes: string
  invoiced: boolean
  created_at: string
}

export interface TimeEntryCreate {
  customer_id: string
  description: string
  date: string
  hours: number
  hourly_rate?: number
  notes?: string
}

export interface TimeEntryUpdate extends Partial<TimeEntryCreate> {
  invoiced?: boolean
}

export interface Activity {
  id: string
  customer_id: string
  type: string
  title: string
  description: string | null
  created_at: string
}

export interface ActivityCreate {
  customer_id: string
  type: string
  title: string
  description?: string
}

export interface TimeEntrySummary {
  customer_id: string
  customer_name: string
  total_hours: number
  total_amount: number
  uninvoiced_hours: number
}

export type ExpenseCategory =
  | 'hosting'
  | 'domain'
  | 'software'
  | 'lizenz'
  | 'hardware'
  | 'ki_api'
  | 'werbung'
  | 'buero'
  | 'reise'
  | 'sonstige'

export interface Expense {
  id: string
  description: string
  category: ExpenseCategory
  amount: number
  date: string
  vendor: string | null
  recurring: boolean
  notes: string | null
  created_at: string
}

export interface ExpenseCreate {
  description: string
  category: ExpenseCategory
  amount: number
  date: string
  vendor?: string
  recurring?: boolean
  notes?: string
}

export interface ExpenseUpdate extends Partial<ExpenseCreate> {}

export interface Attachment {
  id: string
  customer_id: string | null
  order_id: string | null
  contract_id: string | null
  filename: string
  original_name: string
  content_type: string
  size: number
  created_at: string
}

export interface ExpenseSummary {
  year: number
  total: number
  by_category: { category: string; total: number }[]
  by_month: { month: number; total: number }[]
}

export interface EmailTemplate {
  id: string
  name: string
  subject: string
  body: string
  category: string
  created_at: string
}

export interface EmailTemplateCreate {
  name: string
  subject: string
  body: string
  category: string
}

export interface EmailTemplateUpdate {
  name?: string
  subject?: string
  body?: string
  category?: string
}
