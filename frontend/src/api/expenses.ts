import { api } from './client'
import type { Expense, ExpenseCreate, ExpenseUpdate, ExpenseSummary, PaginatedResponse } from '../types'

export async function getExpenses(params?: {
  page?: number
  page_size?: number
  search?: string
  category?: string
  from?: string
  to?: string
}): Promise<PaginatedResponse<Expense>> {
  const response = await api.get('/expenses', { params })
  return response.data
}

export async function getExpense(id: string): Promise<Expense> {
  const response = await api.get(`/expenses/${id}`)
  return response.data
}

export async function createExpense(data: ExpenseCreate): Promise<Expense> {
  const response = await api.post('/expenses', data)
  return response.data
}

export async function updateExpense(id: string, data: ExpenseUpdate): Promise<Expense> {
  const response = await api.put(`/expenses/${id}`, data)
  return response.data
}

export async function deleteExpense(id: string): Promise<void> {
  await api.delete(`/expenses/${id}`)
}

export async function getExpenseSummary(year: number): Promise<ExpenseSummary> {
  const response = await api.get('/expenses/summary', { params: { year } })
  return response.data
}
