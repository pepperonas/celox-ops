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

export async function generateQuotePdf(id: string): Promise<{ quote_pdf_path: string }> {
  const response = await api.post(`/orders/${id}/generate-quote-pdf`)
  return response.data
}

export async function sendQuoteEmail(
  id: string,
  data: { to_email: string; subject?: string; message?: string },
): Promise<void> {
  await api.post(`/orders/${id}/send-quote-email`, data)
}

export async function downloadQuotePdf(id: string): Promise<void> {
  const response = await api.get(`/orders/${id}/quote-pdf`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `Angebot-${id}.pdf`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function viewQuotePdf(id: string): Promise<void> {
  const response = await api.get(`/orders/${id}/quote-pdf`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  window.open(url, '_blank')
}
