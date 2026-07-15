import { api } from './client'
import type {
  OutreachTemplate,
  OutreachTemplateCreate,
  OutreachTemplateUpdate,
} from '../types'

export async function getOutreachTemplates(): Promise<OutreachTemplate[]> {
  const res = await api.get('/outreach/templates')
  return res.data
}

export async function createOutreachTemplate(
  data: OutreachTemplateCreate,
): Promise<OutreachTemplate> {
  const res = await api.post('/outreach/templates', data)
  return res.data
}

export async function updateOutreachTemplate(
  id: string,
  data: OutreachTemplateUpdate,
): Promise<OutreachTemplate> {
  const res = await api.put(`/outreach/templates/${id}`, data)
  return res.data
}

export async function deleteOutreachTemplate(id: string): Promise<void> {
  await api.delete(`/outreach/templates/${id}`)
}

/** Zählt eine Nutzung (Copy) hoch. */
export async function markOutreachCopied(id: string): Promise<OutreachTemplate> {
  const res = await api.post(`/outreach/templates/${id}/copied`)
  return res.data
}

/** Legt die Standard-Templates an (idempotent) und gibt die aktuelle Liste zurück. */
export async function seedOutreachTemplates(): Promise<OutreachTemplate[]> {
  const res = await api.post('/outreach/templates/seed')
  return res.data
}
