import { api } from './client'

export interface DocumentTemplate {
  id: string
  name: string
  category: string
  description: string | null
  is_system: boolean
  created_at: string
}

export async function getDocumentTemplates(): Promise<DocumentTemplate[]> {
  const response = await api.get('/documents/templates')
  return response.data
}

export async function seedDocumentTemplates(): Promise<{ created: number; total: number }> {
  const response = await api.post('/documents/templates/seed')
  return response.data
}

export async function generateDocument(templateId: string, customerId: string): Promise<void> {
  const response = await api.post('/documents/generate', { template_id: templateId, customer_id: customerId }, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  const disposition = response.headers['content-disposition'] || ''
  const match = disposition.match(/filename="(.+)"/)
  a.download = match ? decodeURIComponent(match[1]) : 'dokument.pdf'
  a.click()
  URL.revokeObjectURL(url)
}

export async function previewDocument(templateId: string, customerId: string): Promise<string> {
  const response = await api.get('/documents/preview', { params: { template_id: templateId, customer_id: customerId } })
  return response.data
}
