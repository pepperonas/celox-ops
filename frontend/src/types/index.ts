export interface Customer {
  id: string
  name: string
  email: string
  phone: string
  company: string
  address: string
  notes: string
  created_at: string
  updated_at: string
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
}

export interface OrderUpdate extends Partial<OrderCreate> {}

export type ContractType = 'hosting' | 'wartung' | 'support' | 'sonstige'
export type ContractStatus = 'aktiv' | 'gekuendigt' | 'ausgelaufen'

export interface Contract {
  id: string
  customer_id: string
  customer_name?: string
  title: string
  type: ContractType
  description: string
  monthly_amount: number
  start_date: string
  end_date: string
  auto_renew: boolean
  notice_period_days: number
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
  start_date?: string
  end_date?: string
  auto_renew?: boolean
  notice_period_days?: number
}

export interface ContractUpdate extends Partial<ContractCreate> {}

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
}

export interface InvoiceUpdate extends Partial<InvoiceCreate> {}

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
