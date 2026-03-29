import { api } from './client'
import type { Attachment } from '../types'

export async function uploadAttachment(
  file: File,
  refs: { customer_id?: string; order_id?: string; contract_id?: string },
): Promise<Attachment> {
  const formData = new FormData()
  formData.append('file', file)
  if (refs.customer_id) formData.append('customer_id', refs.customer_id)
  if (refs.order_id) formData.append('order_id', refs.order_id)
  if (refs.contract_id) formData.append('contract_id', refs.contract_id)

  const res = await api.post('/attachments', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listAttachments(params: {
  customer_id?: string
  order_id?: string
  contract_id?: string
}): Promise<Attachment[]> {
  const res = await api.get('/attachments', { params })
  return res.data
}

export async function downloadAttachment(id: string, filename: string): Promise<void> {
  const res = await api.get(`/attachments/${id}/download`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function deleteAttachment(id: string): Promise<void> {
  await api.delete(`/attachments/${id}`)
}
