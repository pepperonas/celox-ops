import { api } from './client'
import type { PaginatedResponse, Todo, TodoCreate, TodoUpdate } from '../types'

export async function getTodos(params?: {
  status?: 'offen' | 'erledigt'
  customer_id?: string
  lead_id?: string
  overdue?: boolean
  search?: string
  page_size?: number
}): Promise<PaginatedResponse<Todo>> {
  const r = await api.get('/todos', { params })
  return r.data
}

export async function getTodoStats(): Promise<{ open: number; overdue: number; due_today: number }> {
  const r = await api.get('/todos/stats')
  return r.data
}

export async function createTodo(data: TodoCreate): Promise<Todo> {
  const r = await api.post('/todos', data)
  return r.data
}

export async function updateTodo(id: string, data: TodoUpdate): Promise<Todo> {
  const r = await api.put(`/todos/${id}`, data)
  return r.data
}

export async function toggleTodo(id: string, done: boolean): Promise<Todo> {
  const r = await api.post(`/todos/${id}/toggle`, { done })
  return r.data
}

export async function deleteTodo(id: string): Promise<void> {
  await api.delete(`/todos/${id}`)
}
