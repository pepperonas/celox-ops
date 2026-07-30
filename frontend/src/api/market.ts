import { api } from './client'

/* Marktradar — importierter Recherchekatalog (Repo business-opportunities).
   Die Typen spiegeln `schemas/market.py`; Aggregate kommen fertig vom Server,
   damit Diagramm und Trefferliste garantiert derselben Filterung folgen. */

export type MarketStatus = 'neu' | 'gesichtet' | 'vorgemerkt' | 'in_pipeline' | 'verworfen'

export interface MarketProduct {
  id: string
  catalog_id: string
  produkt: string
  hersteller: string
  vendor: string
  vendor_slug: string
  konzern: string | null
  kategorie: string
  ref_url: string
  ref_status: 'oeffentlich' | 'teilweise' | 'auf_anfrage' | 'unklar'
  url_ok: boolean
  url_geprueft: string | null
  refs: number
  kunden: string | null
  zielgruppe: string | null
  branchen: string[]
  prozesse: string[]
  nutzer: string[]
  pains: string[]
  ki: string[]
  nutzen: string | null
  integration: string | null
  int_level: 'leicht' | 'mittel' | 'schwer'
  notiz: string | null
  lead: number
  business: number
  prio: 'A' | 'B' | 'C'
  dach: string | null
  score: number
  breakdown: { key: string; value: number; weight: number; points: number }[]
  marketplace: boolean
  mp_evidence: string[]
  reg: string[]
  self_compete: boolean
  /* Angereichert von der Herstellerseite (nicht aus dem Katalog). Fehlt ein Wert,
     wurde er nicht sicher gefunden — dann steht hier null, kein Platzhalter. */
  website: string | null
  email: string | null
  email_status: string | null
  phone: string | null
  decision_maker: string | null
  employee_count: number | null
  contact_evidence: Record<string, { quelle: string; zitat?: string }> | null
  contact_checked_at: string | null
  status: MarketStatus
  ops_note: string | null
  rainmaker_lead_id: string | null
  pushed_at: string | null
}

export interface MarketBucket { label: string; value: number; key?: string }

export interface MarketStats {
  produkte: number
  prio_a: number
  verzeichnisse: number
  hersteller: number
  kategorien: number
  referenzen: number
  marketplace: number
  regulatorik: number
  integration_leicht: number
  offen: number
  in_pipeline: number
  avg_lead: number
  avg_business: number
  avg_score: number
  branchen: MarketBucket[]
  kategorien_top: MarketBucket[]
  reg_top: MarketBucket[]
  lead_hist: MarketBucket[]
  business_hist: MarketBucket[]
  score_bins: MarketBucket[]
  prio_bins: MarketBucket[]
  int_bins: MarketBucket[]
  status_bins: MarketBucket[]
}

export interface MarketBaustein {
  nr: number
  titel: string
  was: string | null
  warum: string | null
  vorsicht: string | null
  aufwand: string | null
  catalog_ids: string[]
  treffer: number
  reach: number
  avg_score: number
  kategorien: number
}

export interface MarketVendor {
  vendor: string
  vendor_slug: string
  konzern: string | null
  produkte: number
  refs: number
  avg_lead: number
  avg_score: number
  marketplace: boolean
  kategorien: string[]
  reg: string[]
  catalog_ids: string[]
}

export interface MarketKonzern {
  konzern: string
  konzern_slug: string
  produkte: number
  refs: number
  marketplace: boolean
  namen: string[]
  catalog_ids: string[]
}

export interface MarketCategory {
  kategorie: string
  produkte: number
  refs: number
  avg_score: number
  avg_business: number
  prio_a: number
  marketplace: number
  oeffentlich: number
  top: { catalog_id: string; produkt: string; score: number; ki: string | null }[]
  prozesse: MarketBucket[]
  risiken: { catalog_id: string; produkt: string; grund: string[] }[]
}

export interface MarketFacets {
  kategorien: string[]
  branchen: string[]
  regulatorik: string[]
  ref_status: string[]
  integration: string[]
  bearbeitung: MarketStatus[]
  stand: string | null
  gesamt: number
}

export interface ToPipelineResult {
  lead_id: string
  company: string
  created: boolean
  duplicate_reason: string | null
}

/** Filterwerte, wie sie an alle Radar-Endpunkte gehen. */
export interface MarketQuery {
  q?: string
  kategorie?: string
  branche?: string
  regulatorik?: string
  prio?: string
  integration?: string
  ref_status?: string
  bearbeitung?: string
  marketplace?: boolean
  hat_regulatorik?: boolean
  min_lead?: number
  min_business?: number
  min_refs?: number
  baustein?: number
}

const params = (q: MarketQuery) => ({ params: q })

export const getMarketProducts = (q: MarketQuery = {}, sort_by = 'score', sort_dir = 'desc') =>
  api.get<MarketProduct[]>('/market/products', { params: { ...q, sort_by, sort_dir } }).then((r) => r.data)

export const getMarketStats = (q: MarketQuery = {}) =>
  api.get<MarketStats>('/market/stats', params(q)).then((r) => r.data)

export const getMarketBausteine = (q: MarketQuery = {}) =>
  api.get<MarketBaustein[]>('/market/bausteine', params(q)).then((r) => r.data)

export const getMarketVendors = (q: MarketQuery = {}) =>
  api.get<MarketVendor[]>('/market/vendors', params(q)).then((r) => r.data)

export const getMarketKonzerne = (q: MarketQuery = {}) =>
  api.get<MarketKonzern[]>('/market/konzerne', params(q)).then((r) => r.data)

export const getMarketCategories = (q: MarketQuery = {}) =>
  api.get<MarketCategory[]>('/market/categories', params(q)).then((r) => r.data)

export const getMarketFacets = () =>
  api.get<MarketFacets>('/market/facets').then((r) => r.data)

export const updateMarketProduct = (id: string, data: { status?: MarketStatus; ops_note?: string | null }) =>
  api.patch<MarketProduct>(`/market/products/${id}`, data).then((r) => r.data)

export const marketToPipeline = (
  id: string,
  body: { force?: boolean; priority?: string; note?: string } = {},
) => api.post<ToPipelineResult>(`/market/products/${id}/to-pipeline`, body).then((r) => r.data)
