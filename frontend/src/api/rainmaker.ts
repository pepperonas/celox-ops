import { api } from './client'
import type {
  RainmakerLead,
  RainmakerLeadCreate,
  RainmakerLeadUpdate,
  RainmakerActivity,
  RainmakerActivityCreate,
  RainmakerActivityComplete,
  RainmakerTodayResponse,
  RainmakerDreamResponse,
  RainmakerStats,
  RainmakerSettings,
  RainmakerSettingsUpdate,
  RainmakerTemplate,
  RainmakerTemplateCreate,
  RainmakerTemplateUpdate,
  RainmakerGoal,
  RainmakerGoalCreate,
  RainmakerGoalUpdate,
  LinkedInImportRow,
  LinkedInPreviewRow,
  LinkedInImportResult,
  DiscoveredCandidate,
  LeadDiscoveryResult,
  DuplicateGroup,
  DuplicateMergeResult,
  AiDiscoverResponse,
  AiUsageResponse,
  PaginatedResponse,
} from '../types'

export async function aiDiscoverPreview(brief: string, useWebSearch = false, model?: string): Promise<AiDiscoverResponse> {
  const response = await api.post('/rainmaker/discover/ai/preview', { brief, use_web_search: useWebSearch, model })
  return response.data
}

export async function getAiUsage(): Promise<AiUsageResponse> {
  const response = await api.get('/rainmaker/ai/usage')
  return response.data
}

export async function verifyLeadEmail(id: string): Promise<RainmakerLead> {
  const response = await api.post(`/rainmaker/leads/${id}/verify-email`)
  return response.data
}

export async function verifyAllEmails(onlyUnchecked = true): Promise<{ checked: number; by_status: Record<string, number> }> {
  const response = await api.post('/rainmaker/leads/verify-emails', null, { params: { only_unchecked: onlyUnchecked } })
  return response.data
}

export async function getDuplicates(): Promise<DuplicateGroup[]> {
  const response = await api.get('/rainmaker/duplicates')
  return response.data
}

export async function mergeDuplicates(
  keeperId: string,
  duplicateIds: string[],
): Promise<DuplicateMergeResult> {
  const response = await api.post('/rainmaker/duplicates/merge', {
    keeper_id: keeperId,
    duplicate_ids: duplicateIds,
  })
  return response.data
}

export async function getRainmakerLeads(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  priority?: string
}): Promise<PaginatedResponse<RainmakerLead>> {
  const response = await api.get('/rainmaker/leads', { params })
  return response.data
}

export async function getRainmakerLead(id: string): Promise<RainmakerLead> {
  const response = await api.get(`/rainmaker/leads/${id}`)
  return response.data
}

export async function createRainmakerLead(
  data: RainmakerLeadCreate,
  force = false,
): Promise<RainmakerLead> {
  const response = await api.post('/rainmaker/leads', data, { params: force ? { force: true } : {} })
  return response.data
}

export async function updateRainmakerLead(
  id: string,
  data: RainmakerLeadUpdate,
): Promise<RainmakerLead> {
  const response = await api.put(`/rainmaker/leads/${id}`, data)
  return response.data
}

export async function deleteRainmakerLead(id: string): Promise<void> {
  await api.delete(`/rainmaker/leads/${id}`)
}

// --- LinkedIn-Import ---
export async function previewLinkedInImport(file: File): Promise<LinkedInPreviewRow[]> {
  const formData = new FormData()
  formData.append('file', file)
  // Gotcha: Default-Content-Type des Clients überschreiben, sonst fehlt die multipart boundary
  const response = await api.post('/rainmaker/import/linkedin/preview', formData, {
    headers: { 'Content-Type': undefined },
  })
  return response.data
}

export async function importLinkedInLeads(rows: LinkedInImportRow[]): Promise<LinkedInImportResult> {
  const response = await api.post('/rainmaker/import/linkedin', { rows })
  return response.data
}

// --- Lead-Discovery (automatische Suche) ---
export async function discoverLeadsPreview(params: {
  source: 'osm' | 'google'; category: string; location: string; limit?: number
}): Promise<DiscoveredCandidate[]> {
  const response = await api.post('/rainmaker/discover/preview', params)
  return response.data
}

export async function importDiscoveredLeads(
  rows: DiscoveredCandidate[], segment?: string,
): Promise<LeadDiscoveryResult> {
  const response = await api.post('/rainmaker/discover/import', { rows, segment })
  return response.data
}

// --- Activities ---
export async function getLeadActivities(leadId: string): Promise<RainmakerActivity[]> {
  const response = await api.get(`/rainmaker/leads/${leadId}/activities`)
  return response.data
}

export async function createLeadActivity(
  leadId: string,
  data: RainmakerActivityCreate,
): Promise<RainmakerActivity> {
  const response = await api.post(`/rainmaker/leads/${leadId}/activities`, data)
  return response.data
}

export async function deleteActivity(id: string): Promise<void> {
  await api.delete(`/rainmaker/activities/${id}`)
}

/** Logs an activity as done. Returns the updated lead (with recomputed next action). */
export async function completeActivity(
  id: string,
  data: RainmakerActivityComplete,
): Promise<RainmakerLead> {
  const response = await api.post(`/rainmaker/activities/${id}/complete`, data)
  return response.data
}

// --- "Heute" / activation engine ---
export async function getRainmakerToday(): Promise<RainmakerTodayResponse> {
  const response = await api.get('/rainmaker/today')
  return response.data
}

export async function getRainmakerStats(): Promise<RainmakerStats> {
  const response = await api.get('/rainmaker/stats')
  return response.data
}

// --- Traumziel (dream goal) ---
export async function getRainmakerDream(): Promise<RainmakerDreamResponse> {
  const response = await api.get('/rainmaker/dream')
  return response.data
}

// --- Settings ---
export async function getRainmakerSettings(): Promise<RainmakerSettings> {
  const response = await api.get('/rainmaker/settings')
  return response.data
}

export async function updateRainmakerSettings(data: RainmakerSettingsUpdate): Promise<RainmakerSettings> {
  const response = await api.put('/rainmaker/settings', data)
  return response.data
}

// --- Templates ---
export async function getRainmakerTemplates(): Promise<RainmakerTemplate[]> {
  const response = await api.get('/rainmaker/templates')
  return response.data
}

export async function createRainmakerTemplate(data: RainmakerTemplateCreate): Promise<RainmakerTemplate> {
  const response = await api.post('/rainmaker/templates', data)
  return response.data
}

export async function updateRainmakerTemplate(id: string, data: RainmakerTemplateUpdate): Promise<RainmakerTemplate> {
  const response = await api.put(`/rainmaker/templates/${id}`, data)
  return response.data
}

export async function deleteRainmakerTemplate(id: string): Promise<void> {
  await api.delete(`/rainmaker/templates/${id}`)
}

// --- Goals (Akquise-Ziele) ---
export async function getRainmakerGoals(): Promise<RainmakerGoal[]> {
  const response = await api.get('/rainmaker/goals')
  return response.data
}

export async function seedRainmakerGoals(): Promise<RainmakerGoal[]> {
  const response = await api.post('/rainmaker/goals/seed')
  return response.data
}

export async function createRainmakerGoal(data: RainmakerGoalCreate): Promise<RainmakerGoal> {
  const response = await api.post('/rainmaker/goals', data)
  return response.data
}

export async function updateRainmakerGoal(id: string, data: RainmakerGoalUpdate): Promise<RainmakerGoal> {
  const response = await api.put(`/rainmaker/goals/${id}`, data)
  return response.data
}

export async function deleteRainmakerGoal(id: string): Promise<void> {
  await api.delete(`/rainmaker/goals/${id}`)
}
