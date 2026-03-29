import { api } from './client'

export interface CustomerProfitability {
  customer_id: string
  customer_name: string
  revenue: number
  expenses: number
  hours_logged: number
  ai_hours: number
  invoices_count: number
  effective_hourly_rate: number
  profit: number
}

export interface ForecastData {
  monthly_recurring: number
  annual_recurring: number
  pipeline_value: number
  pipeline_count: number
  forecast_3m: number
  forecast_6m: number
  forecast_12m: number
  leads_count: number
}

export async function getProfitability(): Promise<CustomerProfitability[]> {
  const res = await api.get('/dashboard/profitability')
  return res.data
}

export async function getForecast(): Promise<ForecastData> {
  const res = await api.get('/dashboard/forecast')
  return res.data
}
