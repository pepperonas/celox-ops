export interface Customer {
  id: number
  name: string
  firma: string
  email: string
  telefon: string
  adresse: string
  plz: string
  ort: string
  land: string
  notizen: string
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  name: string
  firma?: string
  email?: string
  telefon?: string
  adresse?: string
  plz?: string
  ort?: string
  land?: string
  notizen?: string
}

export interface CustomerUpdate extends Partial<CustomerCreate> {}

export type OrderStatus = 'angebot' | 'beauftragt' | 'in_arbeit' | 'abgeschlossen' | 'storniert'

export interface Order {
  id: number
  customer_id: number
  customer_name?: string
  titel: string
  beschreibung: string
  status: OrderStatus
  betrag: number
  stundensatz: number
  start_datum: string
  end_datum: string
  notizen: string
  created_at: string
  updated_at: string
}

export interface OrderCreate {
  customer_id: number
  titel: string
  beschreibung?: string
  status?: OrderStatus
  betrag?: number
  stundensatz?: number
  start_datum?: string
  end_datum?: string
  notizen?: string
}

export interface OrderUpdate extends Partial<OrderCreate> {}

export type ContractType = 'hosting' | 'wartung' | 'support' | 'sonstige'
export type ContractStatus = 'aktiv' | 'gekuendigt' | 'ausgelaufen'

export interface Contract {
  id: number
  customer_id: number
  customer_name?: string
  titel: string
  beschreibung: string
  typ: ContractType
  status: ContractStatus
  monatlicher_betrag: number
  start_datum: string
  end_datum: string
  auto_verlaengerung: boolean
  kuendigungsfrist_tage: number
  notizen: string
  created_at: string
  updated_at: string
}

export interface ContractCreate {
  customer_id: number
  titel: string
  beschreibung?: string
  typ: ContractType
  status?: ContractStatus
  monatlicher_betrag?: number
  start_datum?: string
  end_datum?: string
  auto_verlaengerung?: boolean
  kuendigungsfrist_tage?: number
  notizen?: string
}

export interface ContractUpdate extends Partial<ContractCreate> {}

export type InvoiceStatus = 'entwurf' | 'gestellt' | 'bezahlt' | 'ueberfaellig' | 'storniert'

export interface InvoicePosition {
  id?: number
  beschreibung: string
  menge: number
  einheit: string
  einzelpreis: number
  gesamt: number
}

export interface Invoice {
  id: number
  customer_id: number
  customer_name?: string
  order_id: number | null
  contract_id: number | null
  rechnungsnummer: string
  titel: string
  status: InvoiceStatus
  positionen: InvoicePosition[]
  netto_betrag: number
  ust_satz: number
  ust_betrag: number
  brutto_betrag: number
  kleinunternehmer: boolean
  rechnungsdatum: string
  faelligkeitsdatum: string
  bezahlt_am: string | null
  notizen: string
  pdf_pfad: string | null
  created_at: string
  updated_at: string
}

export interface InvoiceCreate {
  customer_id: number
  order_id?: number | null
  contract_id?: number | null
  titel: string
  status?: InvoiceStatus
  positionen: InvoicePosition[]
  kleinunternehmer?: boolean
  rechnungsdatum?: string
  faelligkeitsdatum?: string
  notizen?: string
}

export interface InvoiceUpdate extends Partial<InvoiceCreate> {}

export interface DashboardStats {
  umsatz_monat: number
  umsatz_jahr: number
  offene_rechnungen_anzahl: number
  offene_rechnungen_summe: number
  ueberfaellige_rechnungen_anzahl: number
  ueberfaellige_rechnungen_summe: number
  aktive_vertraege_anzahl: number
  aktive_vertraege_monatlich: number
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
