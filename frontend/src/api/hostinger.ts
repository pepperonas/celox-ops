import { api } from './client'

/** Woher der Domainname der Zeile kommt. */
export type DomainConfidence = 'confirmed' | 'same_order' | 'sequence' | 'unmatched'

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
  /** Zugeordnete Domain — die API verknuepft Abo und Domain nicht, siehe backend. */
  domain: string | null
  domain_confidence: DomainConfidence | null
  domain_delta_seconds: number | null
  /** Alle Domains dieser TLD — Auswahl fuer eine Korrektur. */
  domain_candidates: string[]
}

export interface HostingerPreview {
  drafts: HostingerDraft[]
  skipped: string[]
  total: string
  counts: Record<string, number>
  already_imported: number
  all_domains: string[]
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

/**
 * `domains` = korrigierte Zuordnungen {subscription_id: domain}. Der Server
 * prueft sie gegen das echte Portfolio und merkt sie sich fuer kuenftige Laeufe.
 */
export async function hostingerImport(
  refs: string[],
  domains: Record<string, string> = {},
): Promise<HostingerImportResult> {
  const response = await api.post('/expenses/hostinger/import', { refs, domains },
    { timeout: 60_000 })
  return response.data
}
