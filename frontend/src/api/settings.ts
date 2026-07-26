import { api } from './client'

export interface AppSettings {
  default_unit_price: number
  invoice_prefix: string
  google_places_configured: boolean
  google_places_key_hint: string | null
  google_places_calls_this_month: number
  ai_model: string
  ai_monthly_budget_eur: number
  /** Automatische (kostenlose) Website-Analyse nach dem Lead-Import. */
  auto_analyze_websites: boolean
}

export interface AppSettingsUpdate {
  default_unit_price?: number
  invoice_prefix?: string
  // "" entfernt den Key
  google_places_api_key?: string
  ai_model?: string
  ai_monthly_budget_eur?: number
  auto_analyze_websites?: boolean
}

export async function getSettings(): Promise<AppSettings> {
  const response = await api.get('/settings')
  return response.data
}

export async function updateSettings(data: AppSettingsUpdate): Promise<AppSettings> {
  const response = await api.put('/settings', data)
  return response.data
}
