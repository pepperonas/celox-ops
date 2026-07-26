import { api } from './client'

export interface WebFinding { category: string; issue: string; severity: string }
export interface WebCategory {
  key: string; label: string; score: number; weight: number; findings: WebFinding[]
}
export interface WebRecommendation {
  priority: string; icon: string; category: string; text: string
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
}
export interface AnalysisEnvelope {
  analysis: WebsiteAnalysis | null
  previous_score: number | null
  previous_at?: string | null
  history_count?: number
}

export async function analyzeLeadWebsite(leadId: string): Promise<AnalysisEnvelope> {
  const r = await api.post(`/rainmaker/leads/${leadId}/analyze-website`)
  return r.data
}

export async function getLeadWebsiteAnalysis(leadId: string): Promise<AnalysisEnvelope> {
  const r = await api.get(`/rainmaker/leads/${leadId}/website-analysis`)
  return r.data
}
