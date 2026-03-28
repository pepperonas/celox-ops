import { api } from './client'

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

export async function exportEuerCsv(year: number): Promise<void> {
  const response = await api.get('/euer/export', {
    params: { year, format: 'csv' },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `euer_${year}.csv`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
