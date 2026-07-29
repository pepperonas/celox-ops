import { api } from './client'

export interface TrashItem {
  id: string
  company: string
  contact_name: string | null
  status: string
  deleted_at: string | null
  deleted_by: string | null
  days_left: number
}

export interface TrashResponse {
  retention_days: number
  items: TrashItem[]
}

export interface LeadChange {
  id: string
  lead_id: string | null
  lead_company: string
  actor: string
  actor_role: string
  action: 'update' | 'delete' | 'restore' | 'create'
  changes: Record<string, { old: unknown; new: unknown }>
  reverted_at: string | null
  created_at: string | null
}

export interface RevertResult {
  reverted_fields: string[]
  /** Felder, die seit der Änderung von jemand anderem angefasst wurden — die
   *  Rücknahme lässt sie bewusst stehen, statt fremde Arbeit zu überschreiben. */
  skipped_fields: string[]
}

export const getLeadTrash = async (): Promise<TrashResponse> =>
  (await api.get<TrashResponse>('/rainmaker/leads/trash')).data

export const restoreLead = async (id: string): Promise<void> => {
  await api.post(`/rainmaker/leads/${id}/restore`)
}

export const purgeLead = async (id: string): Promise<void> => {
  await api.delete(`/rainmaker/leads/${id}/purge`)
}

export const getLeadChanges = async (limit = 100): Promise<LeadChange[]> =>
  (await api.get<LeadChange[]>('/rainmaker/lead-changes', { params: { limit } })).data

export const revertLeadChange = async (id: string): Promise<RevertResult> =>
  (await api.post<RevertResult>(`/rainmaker/lead-changes/${id}/revert`)).data
