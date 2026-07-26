import { api } from './client'

export interface WebFinding { category: string; issue: string; severity: string }
export interface WebCategory {
  key: string; label: string; score: number; weight: number; findings: WebFinding[]
}
export interface WebRecommendation {
  priority: string; icon: string; category: string; text: string
}
export interface AiDimension { key: string; label: string; score: number }
export interface AiReview {
  score: number
  dimensions: AiDimension[]
  summary: string
  strengths: string[]
  weaknesses: string[]
  version: string
}
export interface PageSpeedMetric { label: string; value: string; score: number | null }
export interface PageSpeedField { label: string; percentile: number | null; category: string | null }
export interface PageSpeedResult {
  scores: Record<string, number>
  metrics: PageSpeedMetric[]
  /** CrUX-Felddaten echter Nutzer — einzige Quelle für INP (fehlt bei wenig Traffic). */
  field_metrics?: PageSpeedField[]
  field_source?: 'url' | 'origin' | null
  strategy?: string | null
}
export interface WebsiteAnalysis {
  id: string
  analyzed_at: string | null
  analysis_version: string
  url: string
  overall_score: number
  rating: string
  has_critical: boolean
  categories: WebCategory[]
  findings: WebFinding[]
  technologies: string[]
  recommendations: WebRecommendation[]
  meta: Record<string, unknown>
  ai_review: AiReview | null
  pagespeed: PageSpeedResult | null
}
export interface AnalysisDiff {
  score_delta: number
  category_deltas: Record<string, number>
  new_findings: WebFinding[]
  resolved_findings: WebFinding[]
}
export interface AnalysisEnvelope {
  analysis: WebsiteAnalysis | null
  previous_score: number | null
  previous_at?: string | null
  history_count?: number
  diff?: AnalysisDiff | null
  run?: { model: string; cost_eur: number } | null
  budget?: { spent_eur: number; budget_eur: number } | null
}

export async function analyzeLeadWebsite(
  leadId: string, opts?: { deep?: boolean; pagespeed?: boolean },
): Promise<AnalysisEnvelope> {
  const r = await api.post(`/rainmaker/leads/${leadId}/analyze-website`, null, {
    params: { deep: !!opts?.deep, pagespeed: !!opts?.pagespeed },
  })
  return r.data
}

export async function getLeadWebsiteAnalysis(leadId: string): Promise<AnalysisEnvelope> {
  const r = await api.get(`/rainmaker/leads/${leadId}/website-analysis`)
  return r.data
}
