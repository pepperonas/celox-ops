import { api } from './client'
import type { Order, OrderCreate, OrderUpdate, PaginatedResponse } from '../types'

export async function getOrders(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  customer_id?: string
}): Promise<PaginatedResponse<Order>> {
  const response = await api.get('/orders', { params })
  return response.data
}

export async function getOrder(id: string): Promise<Order> {
  const response = await api.get(`/orders/${id}`)
  return response.data
}

export async function createOrder(data: OrderCreate): Promise<Order> {
  const response = await api.post('/orders', data)
  return response.data
}

export async function updateOrder(id: string, data: OrderUpdate): Promise<Order> {
  const response = await api.put(`/orders/${id}`, data)
  return response.data
}

export async function deleteOrder(id: string): Promise<void> {
  await api.delete(`/orders/${id}`)
}
