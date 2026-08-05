import { api } from './client'
import { filenameFromDisposition } from '../utils/downloadName'
import { saveBlob } from '../utils/saveBlob'

export interface DocumentTemplate {
  id: string
  name: string
  category: string
  description: string | null
  is_system: boolean
  compliance_required: boolean | null
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
  saveBlob(response.data, filenameFromDisposition(response.headers['content-disposition'], 'dokument.pdf'))
}

export async function previewDocument(templateId: string, customerId: string): Promise<string> {
  const response = await api.get('/documents/preview', { params: { template_id: templateId, customer_id: customerId } })
  return response.data
}
