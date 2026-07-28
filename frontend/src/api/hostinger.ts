import { api } from './client'

/** Ein Ausgaben-Entwurf aus einem Hostinger-Abo (Server setzt `duplicate`). */
export interface HostingerDraft {
  description: string
  category: string
  /** Decimal kommt als String aus Pydantic — nie ungeprueft rechnen. */
  amount: string
  date: string
  vendor: string | null
  recurring: boolean
  notes: string | null
  external_ref: string
  subscription_id: string | null
  duplicate: boolean
}

export interface HostingerPreview {
  drafts: HostingerDraft[]
  skipped: string[]
  total: string
  counts: Record<string, number>
  already_imported: number
}

export interface HostingerImportResult {
  created: number
  skipped_duplicates: number
  total: string
  expense_ids: string[]
}

export async function hostingerPreview(): Promise<HostingerPreview> {
  // Drei API-Abrufe bei Hostinger — eigenes, hoeheres Timeout.
  const response = await api.post('/expenses/hostinger/preview', {}, { timeout: 60_000 })
  return response.data
}

export async function hostingerImport(refs: string[]): Promise<HostingerImportResult> {
  const response = await api.post('/expenses/hostinger/import', { refs }, { timeout: 60_000 })
  return response.data
}
