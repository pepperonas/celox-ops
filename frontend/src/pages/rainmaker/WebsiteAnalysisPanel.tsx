import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  analyzeLeadWebsite, getLeadWebsiteAnalysis,
  type AnalysisEnvelope, type WebsiteAnalysis,
} from '../../api/websiteAnalysis'
import {
  PRIORITY_ORDER, ratingLabel, scoreColor, scoreTrend, SEVERITY_COLORS,
} from './webScore'
import WebsiteFactSheet from './WebsiteFactSheet'
import Icon from '../../components/Icon'

const PS_LABELS: Record<string, string> = {
  performance: 'Performance', accessibility: 'Barrierefreiheit',
  'best-practices': 'Best Practices', seo: 'SEO',
}

/** SVG-Fortschrittsring. */
function ScoreRing({ score, size = 96, stroke = 8 }: { score: number; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const color = scoreColor(score)
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--c-border,#333)" strokeWidth={stroke} opacity={0.4} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)}
        transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: 'stroke-dashoffset .6s var(--ease-emphasized,ease)' }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.3} fontWeight={700}>{score}</text>
    </svg>
  )
}

function Skeleton() {
  return (
    <div className="rounded-card p-5 mb-6 border border-border bg-surface-container animate-pulse">
      <div className="flex items-center gap-4 mb-5">
        <div className="w-24 h-24 rounded-full bg-surface-high" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-40 bg-surface-high rounded" />
          <div className="h-3 w-56 bg-surface-high rounded" />
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-16 bg-surface-high rounded-md" />)}
      </div>
    </div>
  )
}

export default function WebsiteAnalysisPanel({ leadId, website, onAnalyzed }: {
  leadId: string; website: string | null; onAnalyzed?: (a: WebsiteAnalysis) => void
}) {
  const [env, setEnv] = useState<AnalysisEnvelope | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [showAllRecs, setShowAllRecs] = useState(false)

  useEffect(() => {
    let alive = true
    getLeadWebsiteAnalysis(leadId)
      .then((e) => { if (alive) setEnv(e) })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [leadId])

  const runAnalyze = useCallback(async (opts?: { deep?: boolean; pagespeed?: boolean }) => {
    setAnalyzing(true)
    try {
      const e = await analyzeLeadWebsite(leadId, opts)
      setEnv(e)
      if (e.analysis) onAnalyzed?.(e.analysis)
      if (e.run) toast.success(`Tiefenanalyse fertig · KI-Kosten ${e.run.cost_eur.toFixed(3)} €`)
    } catch (err: unknown) {
      const ex = err as { response?: { data?: { detail?: string } } }
      toast.error(ex.response?.data?.detail || 'Analyse fehlgeschlagen.')
    }
    setAnalyzing(false)
  }, [leadId, onAnalyzed])

  if (loading || analyzing) return <Skeleton />

  const a = env?.analysis
  if (!a) {
    return (
      <div className="rounded-card p-5 mb-6 border border-border bg-surface-container text-center">
        <p className="text-sm text-text-muted mb-3">
          {website ? 'Noch keine Website-Analyse für diesen Lead.' : 'Kein Website-URL hinterlegt.'}
        </p>
        {website && (
          <div className="flex flex-wrap gap-2 justify-center">
            <button onClick={() => runAnalyze()} className="btn-primary text-sm">Website analysieren</button>
            <button onClick={() => runAnalyze({ deep: true, pagespeed: true })} className="btn-secondary text-sm"
              title="Zusätzlich KI-Qualitätsbewertung + Google PageSpeed (kostet Tokens, dauert länger)"><Icon name="sparkle" size={16} className="mr-1 -mt-0.5" /> Tiefenanalyse
            </button>
          </div>
        )}
      </div>
    )
  }

  const trend = scoreTrend(a.overall_score, env?.previous_score ?? null)
  const recs = showAllRecs ? a.recommendations : a.recommendations.slice(0, 6)
  const analyzedAt = a.analyzed_at ? new Date(a.analyzed_at).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' }) : ''
  const diff = env?.diff ?? null
  const meta = a.meta as { load_time_ms?: number; content_length?: number; reachable?: boolean }
  const loadTimeMs = typeof meta.load_time_ms === 'number' ? meta.load_time_ms : null
  const pageBytes = typeof meta.content_length === 'number' ? meta.content_length : null
  const reachable = typeof meta.reachable === 'boolean' ? meta.reachable : null
  // Scoring transparent machen: die tatsächlich verrechneten Gewichte offenlegen.
  const formula = a.categories.map((c) => `${c.label} ${c.weight}%`).join(' · ')

  return (
    <div className="rounded-card p-5 mb-6 border border-border bg-surface-container">
      {/* KPI-Kopf */}
      <div className="flex flex-wrap items-center gap-4 mb-5">
        <ScoreRing score={a.overall_score} />
        <div className="flex-1 min-w-[180px]">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-text">Website-Analyse</h3>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full"
              style={{ backgroundColor: scoreColor(a.overall_score) + '26', color: scoreColor(a.overall_score) }}>
              {ratingLabel(a.rating)}
            </span>
            {a.has_critical && (
              <span className="text-xs font-semibold text-danger" title="Kritische Probleme gefunden"><Icon name="warning" size={16} className="mr-1 -mt-0.5" /> Kritisch</span>
            )}
            {trend.dir !== 'flat' && (
              <span className="text-xs font-medium" style={{ color: trend.dir === 'up' ? '#22c55e' : '#ef4444' }}
                title="Veränderung gegenüber der Voranalyse">
                <Icon name={trend.dir === 'up' ? 'trendUp' : 'trendDown'} size={13} className="mr-0.5" />{Math.abs(trend.delta)}
              </span>
            )}
          </div>
          <p className="text-xs text-text-muted mt-1"
             title={`Gesamtscore = gewichtetes Mittel der bewerteten Kategorien: ${formula}`}>
            {analyzedAt}{env?.history_count ? ` · ${env.history_count} Analyse${env.history_count > 1 ? 'n' : ''}` : ''} · v{a.analysis_version} · <Icon name="info" size={12} className="mx-0.5" />gewichtet
          </p>
          {a.technologies.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {a.technologies.map((t) => (
                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-high text-text-muted">{t}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <button onClick={() => runAnalyze()} className="btn-secondary text-sm">Neu analysieren</button>
          <button onClick={() => runAnalyze({ deep: true, pagespeed: true })} className="btn-secondary text-sm"
            title="Technik + KI-Qualitätsbewertung + Google PageSpeed (kostet Tokens, dauert länger)"><Icon name="sparkle" size={16} className="mr-1 -mt-0.5" /> Tiefenanalyse
          </button>
        </div>
      </div>

      {/* Kennzahlen der Seite (aus meta) */}
      {(loadTimeMs != null || pageBytes != null || reachable != null) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mb-4 text-xs text-text-muted">
          {reachable != null && (
            <span>Erreichbarkeit: <span className={reachable ? 'text-text' : 'text-danger font-medium'}>
              {reachable ? 'erreichbar' : 'nicht erreichbar'}</span></span>
          )}
          {loadTimeMs != null && (
            <span>Ladezeit: <span className="text-text tabular-nums font-medium"
              style={{ color: scoreColor(loadTimeMs > 5000 ? 20 : loadTimeMs > 3000 ? 50 : loadTimeMs > 1500 ? 70 : 95) }}>
              {(loadTimeMs / 1000).toFixed(1)} s</span></span>
          )}
          {pageBytes != null && (
            <span>Seitengröße: <span className="text-text tabular-nums">
              {pageBytes > 1_000_000 ? `${(pageBytes / 1_000_000).toFixed(1)} MB` : `${Math.round(pageBytes / 1000)} KB`}</span></span>
          )}
        </div>
      )}

      {/* Technik-Steckbrief (alle Roh-Signale, aufklappbar) */}
      <WebsiteFactSheet signals={(a.meta as { signals?: never }).signals} />

      {/* Kategorien — aufklappbar, mit Befunden und Veränderung zum Vorlauf */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-5">
        {a.categories.map((c) => {
          const d = env?.diff?.category_deltas?.[c.key]
          return (
            <details key={c.key} className="group rounded-md bg-surface-high/50 overflow-hidden">
              <summary className="flex items-center gap-2 px-2.5 py-2 cursor-pointer list-none md-state"
                       title={`Gewicht ${c.weight}% am Gesamtscore`}>
                <ScoreRing score={c.score} size={40} stroke={4} />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-text truncate">{c.label}</p>
                  <p className="text-[10px] text-text-muted">
                    {c.findings.length} Befund{c.findings.length !== 1 ? 'e' : ''} · Gewicht {c.weight}%
                  </p>
                </div>
                {d != null && d !== 0 && (
                  <span className="text-[10px] font-semibold shrink-0"
                        style={{ color: d > 0 ? '#22c55e' : '#ef4444' }}
                        title="Veränderung gegenüber der vorherigen Analyse">
                    <Icon name={d > 0 ? 'trendUp' : 'trendDown'} size={12} />{Math.abs(d)}
                  </span>
                )}
                <Icon name="chevronRight" size={12}
                      className="text-text-muted shrink-0 transition-transform group-open:rotate-90" />
              </summary>
              <div className="px-2.5 pb-2.5 pt-0.5">
                {c.findings.length === 0 ? (
                  <p className="text-[11px] text-text-muted">Keine Auffälligkeiten.</p>
                ) : (
                  <ul className="space-y-1">
                    {c.findings.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-[11px] text-text-muted">
                        <span className="shrink-0 mt-1 w-1.5 h-1.5 rounded-full"
                              style={{ backgroundColor: SEVERITY_COLORS[f.severity] ?? '#60a5fa' }} />
                        {f.issue}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </details>
          )
        })}
      </div>

      {/* Änderungen gegenüber der vorherigen Analyse */}
      {diff && (diff.new_findings.length > 0 || diff.resolved_findings.length > 0) && (
        <div className="mb-5 grid sm:grid-cols-2 gap-3">
          {diff.new_findings.length > 0 && (
            <div className="rounded-md border border-danger/30 bg-danger/5 p-2.5">
              <p className="text-[11px] font-semibold text-danger mb-1">
                Neu seit letzter Analyse ({diff.new_findings.length})
              </p>
              <ul className="space-y-0.5">
                {diff.new_findings.slice(0, 5).map((f, i) => (
                  <li key={i} className="text-[11px] text-text-muted">• {f.category}: {f.issue}</li>
                ))}
              </ul>
            </div>
          )}
          {diff.resolved_findings.length > 0 && (
            <div className="rounded-md border p-2.5" style={{ borderColor: '#22c55e4d', backgroundColor: '#22c55e0d' }}>
              <p className="text-[11px] font-semibold mb-1" style={{ color: '#22c55e' }}>
                Behoben ({diff.resolved_findings.length})
              </p>
              <ul className="space-y-0.5">
                {diff.resolved_findings.slice(0, 5).map((f, i) => (
                  <li key={i} className="text-[11px] text-text-muted">✓ {f.category}: {f.issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* PageSpeed (Lighthouse) — nur nach Tiefenanalyse */}
      {a.pagespeed && Object.keys(a.pagespeed.scores).length > 0 && (
        <div className="mb-5 rounded-md border border-border bg-surface-high/40 p-3">
          <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">
            PageSpeed{a.pagespeed.strategy ? ` · ${a.pagespeed.strategy}` : ''}
          </p>
          <div className="flex flex-wrap gap-2 mb-2">
            {Object.entries(a.pagespeed.scores).map(([k, v]) => (
              <span key={k} className="text-[11px] font-medium px-2 py-1 rounded"
                style={{ backgroundColor: scoreColor(v) + '22', color: scoreColor(v) }}>
                {PS_LABELS[k] ?? k}: {v}
              </span>
            ))}
          </div>
          {a.pagespeed.field_metrics && a.pagespeed.field_metrics.length > 0 ? (
            <div className="mb-2">
              <p className="text-[10px] text-text-muted mb-1">
                Felddaten echter Nutzer (CrUX, 28 Tage{a.pagespeed.field_source === 'origin' ? ', Domain-Ebene' : ''})
              </p>
              <div className="flex flex-wrap gap-2">
                {a.pagespeed.field_metrics.map((f) => (
                  <span key={f.label} className="text-[11px] px-2 py-0.5 rounded bg-surface-container"
                        title={f.category ?? undefined}>
                    {f.label}: <span className="tabular-nums font-medium"
                      style={{ color: f.category === 'FAST' ? '#22c55e' : f.category === 'SLOW' ? '#ef4444' : '#f59e0b' }}>
                      {f.percentile ?? '–'}</span>
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[10px] text-text-muted mb-2">
              Keine CrUX-Felddaten (u. a. INP) — die Seite hat zu wenig Traffic für Googles Nutzerdatensatz.
            </p>
          )}
          {a.pagespeed.metrics.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1">
              {a.pagespeed.metrics.map((m) => (
                <div key={m.label} className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="text-text-muted truncate" title={m.label}>{m.label}</span>
                  <span className="tabular-nums font-medium shrink-0"
                    style={{ color: m.score == null ? undefined : scoreColor(m.score) }}>{m.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* KI-Qualitätsbewertung — nur nach Tiefenanalyse */}
      {a.ai_review && (
        <div className="mb-5 rounded-md border border-accent/30 bg-accent/5 p-3">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide"><Icon name="sparkle" size={16} className="mr-1 -mt-0.5" /> KI-Qualitätsbewertung</p>
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded"
              style={{ backgroundColor: scoreColor(a.ai_review.score) + '22', color: scoreColor(a.ai_review.score) }}>
              {a.ai_review.score}/100
            </span>
          </div>
          {a.ai_review.summary && <p className="text-sm text-text mb-2">{a.ai_review.summary}</p>}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 mb-2">
            {a.ai_review.dimensions.map((d) => (
              <div key={d.key} className="flex items-center justify-between gap-2 text-xs">
                <span className="text-text-muted truncate" title={d.label}>{d.label}</span>
                <span className="tabular-nums font-medium shrink-0" style={{ color: scoreColor(d.score) }}>{d.score}</span>
              </div>
            ))}
          </div>
          {(a.ai_review.strengths.length > 0 || a.ai_review.weaknesses.length > 0) && (
            <div className="grid sm:grid-cols-2 gap-3 mt-2">
              {a.ai_review.strengths.length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold text-text-muted mb-1">Stärken</p>
                  <ul className="space-y-0.5">
                    {a.ai_review.strengths.map((s, i) => (
                      <li key={i} className="text-xs text-text-muted">✓ {s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {a.ai_review.weaknesses.length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold text-text-muted mb-1">Schwächen</p>
                  <ul className="space-y-0.5">
                    {a.ai_review.weaknesses.map((s, i) => (
                      <li key={i} className="text-xs text-text-muted">• {s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Priorisierte Empfehlungen */}
      {a.recommendations.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Handlungsempfehlungen</p>
          <ul className="space-y-1.5">
            {PRIORITY_ORDER.flatMap((prio) =>
              recs.filter((r) => r.priority === prio).map((r, i) => (
                <li key={`${prio}-${i}`} className="flex items-start gap-2 text-sm">
                  <span className="shrink-0 mt-0.5">{r.icon}</span>
                  <span className="text-text-muted">
                    <span className="text-text font-medium">{r.category}:</span> {r.text}
                  </span>
                </li>
              )),
            )}
          </ul>
          {a.recommendations.length > 6 && (
            <button onClick={() => setShowAllRecs((v) => !v)} className="text-xs text-accent hover:underline mt-2">
              {showAllRecs ? 'Weniger anzeigen' : `Alle ${a.recommendations.length} anzeigen`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Kompaktes Badge für Listen/Karten — liest die denormalisierten Lead-Felder
 * (kein Join, kein Extra-Request). Zeigt auch den Zustand „noch nicht analysiert",
 * damit in der Liste erkennbar ist, wo eine Analyse fehlt.
 */
export function WebScoreBadge({ score, rating, hasCritical, analyzedAt, compact }: {
  score: number | null
  rating?: string | null
  hasCritical?: boolean | null
  analyzedAt?: string | null
  compact?: boolean
}) {
  if (score == null) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded
                       bg-surface-container text-text-muted"
            title="Website noch nicht analysiert"><Icon name="globe" size={16} className="mr-1 -mt-0.5" /> <span className="opacity-70">n. a.</span>
      </span>
    )
  }
  const color = scoreColor(score)
  const when = analyzedAt
    ? new Date(analyzedAt).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' })
    : null
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded"
      style={{ backgroundColor: color + '22', color }}
      title={`Website-Score ${score}/100 · ${ratingLabel(rating)}${when ? ` · zuletzt geprüft ${when}` : ''}${hasCritical ? ' · kritische Probleme' : ''}`}><Icon name="globe" size={16} className="mr-1 -mt-0.5" /> {score}{hasCritical && <Icon name="warning" size={12} className="ml-0.5" />}{!compact && rating ? ` · ${ratingLabel(rating)}` : ''}
    </span>
  )
}
