import { api } from './client'
import type {
  OutreachChannel,
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

/**
 * Setzt die Reihenfolge eines Kanals. Bewusst die vollständige ID-Liste: ein
 * Bulk-Setzen ist atomar, während einzelne PUTs zur Hälfte scheitern und die
 * Liste halb sortiert hinterlassen könnten.
 */
export const reorderOutreachTemplates = async (
  channel: OutreachChannel, ids: string[],
): Promise<OutreachTemplate[]> =>
  (await api.post<OutreachTemplate[]>('/outreach/templates/reorder', { channel, ids })).data

/**
 * Reihenfolge innerhalb der Favoriten. Ohne Kanal — die Sektion ist
 * kanalübergreifend und schreibt `favorite_order`, nicht `sort_order`.
 */
export const reorderOutreachFavorites = async (
  ids: string[],
): Promise<OutreachTemplate[]> =>
  (await api.post<OutreachTemplate[]>('/outreach/templates/favorites/reorder', { ids })).data
