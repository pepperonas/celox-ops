import { api } from './client'
import { filenameFromDisposition } from '../utils/downloadName'
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

/** Nächster KI-Abrechnungsstart (Ende der letzten Abrechnung + 1 Tag) für einen Kunden. */
export async function getUsagePeriodStart(
  customerId: string,
  excludeInvoiceId?: string,
): Promise<{ start: string | null; last_billed_to: string | null }> {
  const params: Record<string, string> = { customer_id: customerId }
  if (excludeInvoiceId) params.exclude_invoice_id = excludeInvoiceId
  const response = await api.get('/invoices/usage-period-start', { params })
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
  const response = await api.post(`/invoices/${id}/generate-pdf`)
  return response.data
}

export async function downloadPdf(id: string): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get(`/invoices/${id}/pdf`, {
    responseType: 'blob',
  })
  return {
    blob: response.data,
    filename: filenameFromDisposition(response.headers['content-disposition'], 'Rechnung.pdf'),
  }
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

export async function downloadReminderPdf(id: string): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get(`/invoices/${id}/reminder-pdf`, { responseType: 'blob' })
  return {
    blob: response.data,
    filename: filenameFromDisposition(response.headers['content-disposition'], 'Mahnung.pdf'),
  }
}

export async function sendInvoiceEmail(
  id: string,
  data: { to_email: string; subject?: string; message?: string; cc?: string[]; bcc?: string[] },
): Promise<void> {
  await api.post(`/invoices/${id}/send-email`, data)
}

export async function sendReminderEmail(
  id: string,
  data: { to_email: string; subject?: string; message?: string; cc?: string[]; bcc?: string[] },
): Promise<void> {
  await api.post(`/invoices/${id}/send-reminder-email`, data)
}

export async function duplicateInvoice(id: string): Promise<Invoice> {
  const response = await api.post(`/invoices/${id}/duplicate`)
  return response.data
}

export async function recordPayment(id: string, amount: number): Promise<Invoice> {
  const response = await api.post(`/invoices/${id}/payment`, { amount })
  return response.data
}

export async function restorePaymentState(
  id: string,
  amountPaid: number,
  status: InvoiceStatus,
): Promise<Invoice> {
  const response = await api.put(`/invoices/${id}/payment-state`, { amount_paid: amountPaid, status })
  return response.data
}

export async function createCreditNote(id: string): Promise<Invoice> {
  const response = await api.post(`/invoices/${id}/credit-note`)
  return response.data
}

// --- Kontoauszug-Import (Zahlungsabgleich) ---
export interface BankMatchProposal {
  invoice_id: string
  invoice_number: string
  customer_name: string
  invoice_total: number
  invoice_open: number
  amount: number
  confidence: 'exact' | 'number' | 'amount'
  reason: string
  booking_date: string
  purpose: string
  counterparty: string | null
}

export interface BankUnmatched {
  booking_date: string
  amount: number
  purpose: string
  counterparty: string | null
  reason: string
}

export interface BankImportPreview {
  proposals: BankMatchProposal[]
  unmatched: BankUnmatched[]
  ignored_debits: number
  transactions_total: number
  open_invoices: number
}

export interface BankAppliedRow {
  invoice_id: string
  invoice_number: string
  amount: number
  previous_amount_paid: number
  previous_status: string
  new_status: string
}

export interface BankImportResult {
  applied: BankAppliedRow[]
  skipped: string[]
}

export async function previewBankStatement(file: File): Promise<BankImportPreview> {
  const form = new FormData()
  form.append('file', file)
  // Content-Type muss undefined sein, damit Axios die multipart-Boundary setzt.
  const response = await api.post('/invoices/bank-import/preview', form, {
    headers: { 'Content-Type': undefined },
  })
  return response.data
}

export async function applyBankMatches(rows: BankMatchProposal[]): Promise<BankImportResult> {
  const response = await api.post('/invoices/bank-import/apply', { rows })
  return response.data
}
