import { api } from './client'
import { saveBlob } from '../utils/saveBlob'

export interface EuerOverview {
  year: number
  revenue_total: number
  expenses_total: number
  profit: number
  revenue_by_month: { month: number; label: string; amount: number }[]
  expenses_by_month: { month: number; label: string; amount: number }[]
  expenses_by_category: { category: string; label: string; amount: number }[]
  quarterly: { quarter: number; label: string; revenue: number; expenses: number; profit: number }[]
}

export async function getEuerOverview(year: number): Promise<EuerOverview> {
  const response = await api.get('/euer/overview', { params: { year } })
  return response.data
}

export async function downloadMonthlyReport(year: number, month: number): Promise<void> {
  const response = await api.get('/dashboard/monthly-report', {
    params: { year, month },
    responseType: 'blob',
  })
  saveBlob(response.data, `Monatsbericht_${year}_${String(month).padStart(2, '0')}.pdf`)
}

export async function exportEuerCsv(year: number): Promise<void> {
  const response = await api.get('/euer/export', {
    params: { year, format: 'csv' },
    responseType: 'blob',
  })
  saveBlob(response.data, `euer_${year}.csv`)
}
