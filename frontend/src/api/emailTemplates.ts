import { api } from './client'
import type { EmailTemplate, EmailTemplateCreate, EmailTemplateUpdate } from '../types'

export async function getEmailTemplates(category?: string): Promise<EmailTemplate[]> {
  const params = category ? { category } : undefined
  const response = await api.get('/email-templates', { params })
  return response.data
}

export async function getEmailTemplate(id: string): Promise<EmailTemplate> {
  const response = await api.get(`/email-templates/${id}`)
  return response.data
}

export async function createEmailTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
  const response = await api.post('/email-templates', data)
  return response.data
}

export async function updateEmailTemplate(id: string, data: EmailTemplateUpdate): Promise<EmailTemplate> {
  const response = await api.put(`/email-templates/${id}`, data)
  return response.data
}

export async function deleteEmailTemplate(id: string): Promise<void> {
  await api.delete(`/email-templates/${id}`)
}

export async function seedEmailTemplates(): Promise<EmailTemplate[]> {
  const response = await api.post('/email-templates/seed')
  return response.data
}
