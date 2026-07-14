export interface Customer {
  id: string
  name: string
  email: string
  phone: string
  company: string
  address: string
  website: string
  token_tracker_url: string
  github_repos: string
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
  github_repos?: string
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
  /** true = automatisch aus dem KI-Import erzeugt (wird bei Re-Import ersetzt). */
  auto?: boolean
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
  tax_exempt: boolean
  tax_amount: number
  total: number
  invoice_date: string
  due_date: string
  pdf_path: string | null
  notes: string
  special_terms: string | null
  service_description: string | null
  token_usage_from: string | null
  token_usage_to: string | null
  github_commits_from: string | null
  github_commits_to: string | null
  selected_tracker_urls: string | null
  selected_github_repos: string | null
  include_activity_chart: boolean
  discount_type: string | null
  discount_value: number | null
  discount_reason: string | null
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
  tax_exempt?: boolean
  invoice_date?: string
  due_date?: string
  notes?: string
  special_terms?: string | null
  service_description?: string | null
  token_usage_from?: string | null
  token_usage_to?: string | null
  github_commits_from?: string | null
  github_commits_to?: string | null
  selected_tracker_urls?: string | null
  selected_github_repos?: string | null
  include_activity_chart?: boolean
  discount_type?: string | null
  discount_value?: number | null
  discount_reason?: string | null
}

export interface InvoiceUpdate extends Partial<InvoiceCreate> {}

export interface GithubRepo {
  full_name: string
  name: string
  private: boolean
  pushed_at: string
}

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
  draft_invoices_count: number
  draft_invoices_sum: number
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
  expense_id: string | null
  filename: string
  original_name: string
  content_type: string
  size: number
  description: string | null
  notes: string | null
  created_at: string
}

export interface ExpenseSummary {
  year: number
  total: number
  by_category: { category: string; total: number }[]
  by_month: { month: number; total: number }[]
}

export interface PagespeedResult {
  id: string
  customer_id: string
  url: string
  strategy: string
  score_performance: number | null
  score_accessibility: number | null
  score_best_practices: number | null
  score_seo: number | null
  pdf_path: string | null
  created_at: string
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

// --------------------------------------------------------------------------- //
//  Rainmaker — Akquise-Aktivierung
// --------------------------------------------------------------------------- //
export type RainmakerLeadStatus =
  | 'new'
  | 'contacted'
  | 'connected'
  | 'in_conversation'
  | 'proposal'
  | 'won'
  | 'lost'
  | 'dormant'

export type RainmakerPriority = 'low' | 'medium' | 'high'

export type RainmakerActivityType =
  | 'call'
  | 'email'
  | 'visit'
  | 'message'
  | 'follow_up'
  | 'note'

export interface RainmakerLead {
  id: string
  company: string
  contact_name: string | null
  role: string | null
  phone: string | null
  email: string | null
  address: string | null
  website: string | null
  source: string | null
  status: RainmakerLeadStatus
  priority: RainmakerPriority
  value_estimate: number | null
  tags: string[] | null
  notes: string | null
  created_at: string
  updated_at: string
  // E-Mail-Qualitätsurteil (SMTP-frei): valid/role/disposable/no_mx/invalid_syntax/unknown/null
  email_status: string | null
  // Verknüpfter Kunde nach Lead→Kunde-Konvertierung
  customer_id: string | null
  // Activation-engine computed fields
  next_action_type: RainmakerActivityType | null
  next_action_due: string | null
  next_action_id: string | null
  needs_next_action: boolean
}

export interface RainmakerLeadCreate {
  company: string
  contact_name?: string | null
  role?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  website?: string | null
  source?: string | null
  status?: RainmakerLeadStatus
  priority?: RainmakerPriority
  value_estimate?: number | null
  tags?: string[] | null
  notes?: string | null
}

export type RainmakerLeadUpdate = Partial<RainmakerLeadCreate>

export type RainmakerActivityStatus = 'planned' | 'done' | 'skipped'

export type RainmakerOutcome =
  | 'reached'
  | 'no_answer'
  | 'positive'
  | 'negative'
  | 'meeting_set'
  | 'proposal_sent'
  | 'not_interested'

export interface RainmakerActivity {
  id: string
  lead_id: string
  goal_id: string | null
  type: RainmakerActivityType
  status: RainmakerActivityStatus
  due_date: string | null
  completed_at: string | null
  outcome: RainmakerOutcome | null
  notes: string | null
  created_at: string
}

export interface RainmakerActivityCreate {
  type: RainmakerActivityType
  due_date?: string | null
  notes?: string | null
  goal_id?: string | null
}

export interface RainmakerActivityComplete {
  outcome?: RainmakerOutcome | null
  notes?: string | null
  next_type?: RainmakerActivityType | null
  next_due?: string | null
  next_goal_id?: string | null
  close_status?: RainmakerLeadStatus | null
}

export interface RainmakerGoal {
  id: string
  name: string
  suggested_type: RainmakerActivityType
  daily_target: number
  active: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface RainmakerGoalCreate {
  name: string
  suggested_type: RainmakerActivityType
  daily_target?: number
  active?: boolean
  sort_order?: number
}

export type RainmakerGoalUpdate = Partial<RainmakerGoalCreate>

// LinkedIn-Import (offizieller Datenexport: ZIP-Archiv oder Connections.csv)
export interface LinkedInMessage {
  date: string
  direction: string
  snippet: string
}

export interface LinkedInImportRow {
  first_name: string
  last_name: string
  url: string
  email: string
  company: string
  position: string
  connected_on: string
  source: 'connection' | 'invitation'
  status: RainmakerLeadStatus
  invited_at: string
  message_count: number
  last_message_at: string
  messages: LinkedInMessage[]
}

export interface LinkedInPreviewRow extends LinkedInImportRow {
  duplicate: boolean
}

export interface DiscoveredCandidate {
  name: string
  website: string | null
  email: string | null
  phone: string | null
  address: string | null
  source: string
  source_ref: string | null
  duplicate: boolean
  duplicate_reason?: string | null   // "email" | "website" | "name"
  email_status?: string | null
  fit_reason?: string | null         // KI-Begründung
}

export interface AiRunCost {
  model: string
  input_tokens: number
  output_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
  web_searches: number
  cost_usd: number
  cost_eur: number
}

export interface AiBudget {
  budget_eur: number
  spent_eur: number
  remaining_eur: number
  warn: boolean
}

export interface AiDiscoverResponse {
  candidates: DiscoveredCandidate[]
  run: AiRunCost
  budget: AiBudget
  notes: string[]
}

export interface AiRunSummary {
  id: string
  brief: string
  model: string
  cost_eur: number
  cost_usd: number
  candidates_found: number
  leads_imported: number
  status: string
  created_at: string
}

export interface AiUsageResponse {
  budget: AiBudget
  runs_this_month: number
  spent_usd: number
  avg_cost_eur: number
  configured: boolean
  model: string
  pricing_source?: string
  recent: AiRunSummary[]
}

export interface ImportSkipped {
  name: string
  reason: string                     // "email" | "website" | "name"
}

export interface LeadDiscoveryResult {
  created: number
  skipped_duplicates: number
  enriched?: number
  skipped_rows?: ImportSkipped[]
}

export interface LinkedInImportResult {
  created: number
  skipped_duplicates: number
  enriched: number
  activities_created: number
  skipped_rows?: ImportSkipped[]
}

export interface DuplicateMember {
  id: string
  company: string
  contact_name: string | null
  role: string | null
  email: string | null
  website: string | null
  phone: string | null
  source: string | null
  status: string
  activity_count: number
  created_at: string | null
}

export interface DuplicateGroup {
  score: number
  reason: 'same_person' | 'firm' | 'colleagues' | 'fuzzy' | string
  suggested_keeper_id: string
  members: DuplicateMember[]
}

export interface DuplicateMergeResult {
  keeper: RainmakerLead
  merged_leads: number
  moved_activities: number
}

export interface DuplicateMergeFailure {
  company: string
  reason: string
}

export interface DuplicateMergeBatchResult {
  merged_groups: number
  deleted_leads: number
  moved_activities: number
  failed: DuplicateMergeFailure[]
}

export interface RainmakerGoalProgress {
  id: string
  name: string
  suggested_type: RainmakerActivityType
  daily_target: number
  done_today: number
}

export interface RainmakerLeadSummary {
  id: string
  company: string
  contact_name: string | null
  phone: string | null
  email: string | null
  address: string | null
  status: RainmakerLeadStatus
  priority: RainmakerPriority
  value_estimate: number | null
}

export interface RainmakerTodayItem {
  activity: RainmakerActivity
  lead: RainmakerLeadSummary
  days_overdue: number
}

export interface RainmakerProgress {
  daily_quota: number
  done_today: number
  current_streak: number
  longest_streak: number
  total_points: number
  freeze_remaining: number
}

export interface RainmakerTodayResponse {
  date: string
  queue: RainmakerTodayItem[]
  rotting: RainmakerLeadSummary[]
  progress: RainmakerProgress
  goals: RainmakerGoalProgress[]
  total_leads: number
}

export type RainmakerReminderChannel = 'email' | 'telegram' | 'push'
export type RainmakerTemplateChannel = 'email' | 'message'

export type RainmakerDreamMode = 'ev' | 'invoices'

export interface RainmakerSettings {
  id: string
  daily_quota: number
  reminder_enabled: boolean
  reminder_time: string
  reminder_channel: RainmakerReminderChannel
  telegram_chat_id: string | null
  freezes_per_month: number
  // Traumziel (dream goal)
  dream_goal_key: string | null
  dream_goal_name: string | null
  dream_goal_price: number
  dream_savings_rate_pct: number
  dream_avg_deal_value: number
  dream_contacts_per_win: number
  dream_start_date: string | null
  dream_mode: RainmakerDreamMode
}

export type RainmakerSettingsUpdate = Partial<Omit<RainmakerSettings, 'id'>>

// Traumziel — expected-value motivation engine (numbers may arrive as strings
// from the API; the page wraps them in Number()).
export interface RainmakerDreamResponse {
  goal_key: string | null
  goal_name: string
  goal_price: number
  savings_rate_pct: number
  avg_deal_value: number
  contacts_per_win: number
  start_date: string
  mode: RainmakerDreamMode
  ev_per_contact: number
  ev_weights: Record<string, number>
  counts_by_type: { type: RainmakerActivityType; count: number }[]
  activities_ev: number
  won_count: number
  won_value: number
  won_ev: number
  invoices_paid: number
  invoices_ev: number
  saved_total: number
  pct: number
  today_ev: number
  pace_per_day: number
  projected_date: string | null
  days_active: number
}

export interface RainmakerTemplate {
  id: string
  channel: RainmakerTemplateChannel
  name: string
  subject: string | null
  body: string
  created_at: string
  updated_at: string
}

export interface RainmakerTemplateCreate {
  channel: RainmakerTemplateChannel
  name: string
  subject?: string | null
  body: string
}

export type RainmakerTemplateUpdate = Partial<RainmakerTemplateCreate>

export interface RainmakerStats {
  activity_by_type: { type: RainmakerActivityType; count: number }[]
  activity_by_day: { date: string; count: number }[]
  funnel: { status: RainmakerLeadStatus; count: number }[]
  total_leads: number
  won_count: number
  lost_count: number
  open_value: number | null
  won_value: number | null
  current_streak: number
  longest_streak: number
  total_points: number
}
