// Technik-Steckbrief der Website-Analyse: zeigt die gespeicherten Roh-Signale
// (meta.signals) kompakt und aufklappbar. Rein präsentational — die Fakten kommen
// unverändert aus `website_signals.extract_signals` im Backend.

import Icon from '../../components/Icon'

interface Tracker { name: string; risk: string }
interface Signals {
  meta?: {
    title?: string; title_length?: number; description?: string; description_length?: number
    canonical?: boolean; robots?: string; noindex?: boolean; lang?: string; charset?: string
    favicon?: boolean; viewport?: boolean; og_present?: boolean; twitter_card?: string
    twitter_present?: boolean
  }
  seo?: {
    headings?: Record<string, number>; images_total?: number; images_without_alt?: number
    structured_data?: string[]; internal_links?: number; external_links?: number
  }
  tech?: {
    cms?: string[]; frameworks?: string[]; server?: string | null; powered_by?: string | null
    cdn?: string[]; wordpress_version?: string | null; https?: boolean
  }
  privacy?: {
    has_impressum?: boolean; has_privacy?: boolean; cmps?: string[]
    has_cookie_banner?: boolean; trackers?: Tracker[]; google_fonts_external?: boolean
  }
  extras?: {
    robots_txt?: boolean | null; sitemap?: boolean | null; sitemap_url?: string
    broken_links?: string[]; links_checked?: number
    redirects?: { url: string; status: number }[]
  }
}

const RISK_COLOR: Record<string, string> = { high: '#ef4444', medium: '#f59e0b', low: '#22c55e' }
const RISK_LABEL: Record<string, string> = { high: 'einwilligungspflichtig', medium: 'Drittinhalt', low: 'unkritisch' }

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className="text-text text-right min-w-0 truncate">{children}</span>
    </div>
  )
}

const yesNo = (v?: boolean | null) =>
  v == null ? '–' : v ? <span style={{ color: '#22c55e' }}>ja</span> : <span className="text-danger">nein</span>

export default function WebsiteFactSheet({ signals }: { signals: Signals | undefined }) {
  if (!signals) return null
  const m = signals.meta ?? {}
  const seo = signals.seo ?? {}
  const tech = signals.tech ?? {}
  const priv = signals.privacy ?? {}
  const ex = signals.extras ?? {}
  const h = seo.headings ?? {}
  const headingStr = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    .filter((k) => (h[k] ?? 0) > 0).map((k) => `${k.toUpperCase()}:${h[k]}`).join(' · ') || '–'
  const trackers = priv.trackers ?? []

  return (
    <details className="group mb-5 rounded-md border border-border bg-surface-high/30">
      <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer list-none md-state">
        <span className="text-xs font-semibold text-text-muted uppercase tracking-wide flex-1">
          Technik-Steckbrief
        </span>
        <span className="text-[10px] text-text-muted">
          {[tech.cms?.[0], tech.frameworks?.[0], tech.cdn?.[0]].filter(Boolean).join(' · ') || 'Details'}
        </span>
        <Icon name="chevronRight" size={12}
              className="text-text-muted transition-transform group-open:rotate-90" />
      </summary>

      <div className="px-3 pb-3 grid md:grid-cols-2 gap-x-6 gap-y-4 text-xs">
        {/* Meta */}
        <div>
          <p className="text-[11px] font-semibold text-text mb-1">Meta &amp; Auffindbarkeit</p>
          <Row label="Titel">{m.title ? `${m.title.slice(0, 60)} (${m.title_length})` : '–'}</Row>
          <Row label="Description">{m.description ? `${m.description_length} Zeichen` : '–'}</Row>
          <Row label="Canonical">{yesNo(m.canonical)}</Row>
          <Row label="Indexierbar">{m.noindex ? <span className="text-danger">nein (noindex)</span> : yesNo(true)}</Row>
          <Row label="OpenGraph">{yesNo(m.og_present)}</Row>
          <Row label="Twitter Card">{m.twitter_card || (m.twitter_present ? 'ja' : '–')}</Row>
          <Row label="Sprache">{m.lang || '–'}</Row>
          <Row label="Zeichensatz">{m.charset || '–'}</Row>
          <Row label="Favicon">{yesNo(m.favicon)}</Row>
          <Row label="robots.txt">{yesNo(ex.robots_txt)}</Row>
          <Row label="sitemap.xml">{yesNo(ex.sitemap)}</Row>
        </div>

        {/* Technik */}
        <div>
          <p className="text-[11px] font-semibold text-text mb-1">Technik</p>
          <Row label="HTTPS">{yesNo(tech.https)}</Row>
          <Row label="CMS">{tech.cms?.length ? tech.cms.join(', ') : '–'}</Row>
          <Row label="Frameworks">{tech.frameworks?.length ? tech.frameworks.join(', ') : '–'}</Row>
          <Row label="Server">{tech.server || '–'}</Row>
          <Row label="X-Powered-By">{tech.powered_by || '–'}</Row>
          <Row label="CDN / Hosting">{tech.cdn?.length ? tech.cdn.join(', ') : '–'}</Row>
          {tech.wordpress_version && <Row label="WP-Version">{tech.wordpress_version}</Row>}
          {ex.redirects && ex.redirects.length > 1 && (
            <Row label="Weiterleitungen">{ex.redirects.length - 1}</Row>
          )}
        </div>

        {/* SEO-Struktur */}
        <div>
          <p className="text-[11px] font-semibold text-text mb-1">SEO-Struktur</p>
          <Row label="Überschriften">{headingStr}</Row>
          <Row label="Bilder">{`${seo.images_total ?? 0} (${seo.images_without_alt ?? 0} ohne ALT)`}</Row>
          <Row label="Strukturierte Daten">{seo.structured_data?.length ? seo.structured_data.join(', ') : '–'}</Row>
          <Row label="Interne Links">{seo.internal_links ?? '–'}</Row>
          <Row label="Externe Links">{seo.external_links ?? '–'}</Row>
          {ex.links_checked != null && (
            <Row label="Linkcheck">
              {(ex.broken_links?.length ?? 0) === 0
                ? <span style={{ color: '#22c55e' }}>{ex.links_checked} geprüft, ok</span>
                : <span className="text-danger">{ex.broken_links?.length} von {ex.links_checked} defekt</span>}
            </Row>
          )}
        </div>

        {/* Datenschutz */}
        <div>
          <p className="text-[11px] font-semibold text-text mb-1">Datenschutz</p>
          <Row label="Impressum">{yesNo(priv.has_impressum)}</Row>
          <Row label="Datenschutzerklärung">{yesNo(priv.has_privacy)}</Row>
          <Row label="Cookie-Banner">{yesNo(priv.has_cookie_banner)}</Row>
          <Row label="CMP">{priv.cmps?.length ? priv.cmps.join(', ') : '–'}</Row>
          <Row label="Google Fonts">{priv.google_fonts_external
            ? <span className="text-danger">extern</span>
            : <span style={{ color: '#22c55e' }}>lokal / keine</span>}</Row>
          {trackers.length > 0 && (
            <div className="mt-1.5">
              <p className="text-text-muted mb-1">Erkannte Dienste ({trackers.length})</p>
              <div className="flex flex-wrap gap-1">
                {trackers.map((t) => (
                  <span key={t.name} className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ backgroundColor: (RISK_COLOR[t.risk] ?? '#888') + '22',
                                 color: RISK_COLOR[t.risk] ?? '#888' }}
                        title={RISK_LABEL[t.risk] ?? t.risk}>
                    {t.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </details>
  )
}
