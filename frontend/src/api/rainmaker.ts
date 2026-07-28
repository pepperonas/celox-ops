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
  DuplicateMergeBatchResult,
  AiDiscoverResponse,
  AiUsageResponse,
  PaginatedResponse,
  AiRunCost,
  AiBudget,
  AnalysisQueueStatus,
  LeadIntakeDraft,
  LeadIntakeResponse,
  LeadIntakeCommitResult,
} from '../types'

export async function aiDiscoverPreview(brief: string, useWebSearch = false, model?: string, enrich = true): Promise<AiDiscoverResponse> {
  const body = { brief, use_web_search: useWebSearch, model, enrich }
  // 502 = Backend gerade nicht erreichbar (z. B. kurzes Deploy-Fenster). Die Anfrage
  // hat den Server nicht erreicht → sicher & kostenfrei erneut versuchen.
  for (let attempt = 0; ; attempt++) {
    try {
      const response = await api.post('/rainmaker/discover/ai/preview', body)
      return response.data
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 502 && attempt < 2) {
        await new Promise((r) => setTimeout(r, 3000))
        continue
      }
      throw err
    }
  }
}

export async function getAiUsage(): Promise<AiUsageResponse> {
  const response = await api.get('/rainmaker/ai/usage')
  return response.data
}

export async function verifyLeadEmail(id: string): Promise<RainmakerLead> {
  const response = await api.post(`/rainmaker/leads/${id}/verify-email`)
  return response.data
}

export async function linkLeadCustomer(leadId: string, customerId: string): Promise<RainmakerLead> {
  const response = await api.post(`/rainmaker/leads/${leadId}/link-customer`, { customer_id: customerId })
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

export async function mergeDuplicatesBatch(
  merges: { keeper_id: string; duplicate_ids: string[] }[],
): Promise<DuplicateMergeBatchResult> {
  const response = await api.post('/rainmaker/duplicates/merge-batch', { merges })
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
  source: 'osm' | 'google'; category: string; location: string; limit?: number; enrich?: boolean
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

// --- Automatische Website-Analyse (Queue) ---
export async function getAnalysisQueue(): Promise<AnalysisQueueStatus> {
  const response = await api.get('/rainmaker/analysis-queue')
  return response.data
}

export async function enqueueMissingAnalyses(): Promise<{
  queued: number; candidates: number; capped: boolean; pending: number
}> {
  const response = await api.post('/rainmaker/analysis-queue/enqueue-missing')
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

// --- Lead-Akquise-Mail (KI-Entwurf + Versand) ---
export interface LeadEmailDraft {
  subject: string
  body: string
  product: string | null
  cached: boolean
  run: AiRunCost
  budget: AiBudget
}

export async function draftLeadEmail(leadId: string, force = false): Promise<LeadEmailDraft> {
  const response = await api.post(`/rainmaker/leads/${leadId}/draft-email`, null, {
    params: { force },
  })
  return response.data
}

export async function sendLeadEmail(
  leadId: string,
  data: { to_email: string; subject: string; message: string; cc?: string[]; bcc?: string[] },
): Promise<{ ok: boolean; sent_to: string }> {
  const response = await api.post(`/rainmaker/leads/${leadId}/send-email`, data)
  return response.data
}

// --- Chat-Import: Lead per KI aus einem Gespraechsverlauf aktualisieren ---
export interface ChatProposalNote { key: string; text: string; preselected: boolean }
export interface ChatProposalActivity {
  key: string; type: string; day: string; direction: string | null
  excerpt: string; fingerprint: string; note: string
  duplicate: boolean; preselected: boolean
}
export interface ChatProposalNext {
  key: string; type: string; due_date: string; reason: string; preselected: boolean
}
export interface ChatProposalField {
  key: string; field: string; label: string; old: string; new: string
  evidence: string; preselected: boolean
}
export interface ChatProposalIgnored { field: string; label: string; reason: string }

export interface ChatProposal {
  notes: ChatProposalNote[]
  activities: ChatProposalActivity[]
  next_action: ChatProposalNext | null
  fields: ChatProposalField[]
  ignored: ChatProposalIgnored[]
  summary: string
}

export interface ChatImportPreview {
  import_id: string
  cached: boolean
  proposal: ChatProposal
  run: AiRunCost
  budget: AiBudget
}

export interface ChatImportResult {
  applied_notes: number
  applied_activities: number
  applied_fields: string[]
  planned_next: boolean
  can_undo: boolean
}

export async function chatImportPreview(
  leadId: string, text: string, images: File[],
): Promise<ChatImportPreview> {
  const form = new FormData()
  form.append('text', text)
  for (const img of images) form.append('images', img, img.name)
  // Content-Type muss undefined sein, damit Axios die multipart-Boundary setzt.
  const response = await api.post(`/rainmaker/leads/${leadId}/chat-import/preview`, form, {
    headers: { 'Content-Type': undefined },
  })
  return response.data
}

export async function chatImportApply(
  leadId: string, importId: string, keys: string[],
): Promise<ChatImportResult> {
  const response = await api.post(
    `/rainmaker/leads/${leadId}/chat-import/${importId}/apply`, { keys })
  return response.data
}

export async function chatImportUndo(leadId: string, importId: string): Promise<void> {
  await api.post(`/rainmaker/leads/${leadId}/chat-import/${importId}/undo`)
}

// --- Lead-Erfassung aus Material („Aus Chat/Screenshot") ---
export async function leadIntakePreview(payload: {
  text: string; hint: string; images: string[]
  website?: string; description?: string; model?: string
}): Promise<LeadIntakeResponse> {
  // Eigenes, hohes Timeout: sechs Screenshots brauchen 30–60 s. Der Default des
  // Clients wuerde vorher abbrechen, obwohl das Backend noch rechnet.
  const response = await api.post('/rainmaker/leads/intake', payload, { timeout: 300_000 })
  return response.data
}

export async function leadIntakeCommit(
  leads: LeadIntakeDraft[], force = false,
): Promise<LeadIntakeCommitResult> {
  const response = await api.post('/rainmaker/leads/intake/commit', { leads, force })
  return response.data
}
