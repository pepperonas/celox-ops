import { api } from './client'

export interface AppSettings {
  default_unit_price: number
  invoice_prefix: string
}

export async function getSettings(): Promise<AppSettings> {
  const response = await api.get('/settings')
  return response.data
}

export async function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  const response = await api.put('/settings', data)
  return response.data
}
