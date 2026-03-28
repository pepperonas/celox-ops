import { api } from './client'
import type { Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus, QuickInvoiceCreate, PaginatedResponse } from '../types'

export async function getInvoices(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  customer_id?: string
}): Promise<PaginatedResponse<Invoice>> {
  const response = await api.get('/invoices', { params })
  return response.data
}

export async function getInvoice(id: string): Promise<Invoice> {
  const response = await api.get(`/invoices/${id}`)
  return response.data
}

export async function createInvoice(data: InvoiceCreate): Promise<Invoice> {
  const response = await api.post('/invoices', data)
  return response.data
}

export async function updateInvoice(id: string, data: InvoiceUpdate): Promise<Invoice> {
  const response = await api.put(`/invoices/${id}`, data)
  return response.data
}

export async function deleteInvoice(id: string): Promise<void> {
  await api.delete(`/invoices/${id}`)
}

export async function generatePdf(id: string): Promise<{ pdf_path: string }> {
  const response = await api.post(`/invoices/${id}/pdf`)
  return response.data
}

export async function downloadPdf(id: string): Promise<Blob> {
  const response = await api.get(`/invoices/${id}/pdf`, {
    responseType: 'blob',
  })
  return response.data
}

export async function createQuickInvoice(data: QuickInvoiceCreate): Promise<Invoice> {
  const response = await api.post('/invoices/quick', data)
  return response.data
}

export async function updateInvoiceStatus(
  id: string,
  status: InvoiceStatus,
): Promise<Invoice> {
  const response = await api.put(`/invoices/${id}/status`, { status })
  return response.data
}

export async function sendReminder(id: string): Promise<Invoice> {
  const response = await api.post(`/invoices/${id}/remind`)
  return response.data
}

export async function generateReminderPdf(id: string): Promise<{ reminder_pdf_path: string }> {
  const response = await api.post(`/invoices/${id}/generate-reminder-pdf`)
  return response.data
}

export async function downloadReminderPdf(id: string): Promise<Blob> {
  const response = await api.get(`/invoices/${id}/reminder-pdf`, { responseType: 'blob' })
  return response.data
}

export async function sendInvoiceEmail(
  id: string,
  data: { to_email: string; subject?: string; message?: string },
): Promise<void> {
  await api.post(`/invoices/${id}/send-email`, data)
}

export async function sendReminderEmail(
  id: string,
  data: { to_email: string; subject?: string; message?: string },
): Promise<void> {
  await api.post(`/invoices/${id}/send-reminder-email`, data)
}
