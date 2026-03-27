import { api } from './client'
import type { Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus, PaginatedResponse } from '../types'

export async function getInvoices(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  customer_id?: number
}): Promise<PaginatedResponse<Invoice>> {
  const response = await api.get('/invoices', { params })
  return response.data
}

export async function getInvoice(id: number): Promise<Invoice> {
  const response = await api.get(`/invoices/${id}`)
  return response.data
}

export async function createInvoice(data: InvoiceCreate): Promise<Invoice> {
  const response = await api.post('/invoices', data)
  return response.data
}

export async function updateInvoice(id: number, data: InvoiceUpdate): Promise<Invoice> {
  const response = await api.put(`/invoices/${id}`, data)
  return response.data
}

export async function deleteInvoice(id: number): Promise<void> {
  await api.delete(`/invoices/${id}`)
}

export async function generatePdf(id: number): Promise<{ pdf_pfad: string }> {
  const response = await api.post(`/invoices/${id}/pdf`)
  return response.data
}

export async function downloadPdf(id: number): Promise<Blob> {
  const response = await api.get(`/invoices/${id}/pdf`, {
    responseType: 'blob',
  })
  return response.data
}

export async function updateInvoiceStatus(
  id: number,
  status: InvoiceStatus,
): Promise<Invoice> {
  const response = await api.patch(`/invoices/${id}/status`, { status })
  return response.data
}
