import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  analyzeLeadWebsite, getLeadWebsiteAnalysis,
  type AnalysisEnvelope, type WebsiteAnalysis,
} from '../../api/websiteAnalysis'
import {
  PRIORITY_ORDER, ratingLabel, scoreColor, scoreTrend, SEVERITY_COLORS,
} from './webScore'

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

  const runAnalyze = useCallback(async () => {
    setAnalyzing(true)
    try {
      const e = await analyzeLeadWebsite(leadId)
      setEnv(e)
      if (e.analysis) onAnalyzed?.(e.analysis)
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
        {website && <button onClick={runAnalyze} className="btn-primary text-sm">Website analysieren</button>}
      </div>
    )
  }

  const trend = scoreTrend(a.overall_score, env?.previous_score ?? null)
  const recs = showAllRecs ? a.recommendations : a.recommendations.slice(0, 6)
  const analyzedAt = a.analyzed_at ? new Date(a.analyzed_at).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' }) : ''

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
              <span className="text-xs font-semibold text-danger" title="Kritische Probleme gefunden">⚠ Kritisch</span>
            )}
            {trend.dir !== 'flat' && (
              <span className="text-xs font-medium" style={{ color: trend.dir === 'up' ? '#22c55e' : '#ef4444' }}
                title="Veränderung gegenüber der Voranalyse">
                {trend.dir === 'up' ? '▲' : '▼'} {Math.abs(trend.delta)}
              </span>
            )}
          </div>
          <p className="text-xs text-text-muted mt-1">
            {analyzedAt}{env?.history_count ? ` · ${env.history_count} Analyse${env.history_count > 1 ? 'n' : ''}` : ''} · v{a.analysis_version}
          </p>
          {a.technologies.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {a.technologies.map((t) => (
                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-high text-text-muted">{t}</span>
              ))}
            </div>
          )}
        </div>
        <button onClick={runAnalyze} className="btn-secondary text-sm">Neu analysieren</button>
      </div>

      {/* Kategorie-Ringe */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
        {a.categories.map((c) => (
          <div key={c.key} className="flex items-center gap-2 rounded-md bg-surface-high/50 px-2.5 py-2" title={`Gewicht ${c.weight}%`}>
            <ScoreRing score={c.score} size={40} stroke={4} />
            <div className="min-w-0">
              <p className="text-xs font-medium text-text truncate">{c.label}</p>
              <p className="text-[10px] text-text-muted">{c.findings.length} Befund{c.findings.length !== 1 ? 'e' : ''}</p>
            </div>
          </div>
        ))}
      </div>

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

/** Kompaktes Badge für Karten/Header (aus den denormalisierten Lead-Feldern). */
export function WebScoreBadge({ score, rating, hasCritical, compact }: {
  score: number | null; rating?: string | null; hasCritical?: boolean | null; compact?: boolean
}) {
  if (score == null) return null
  const color = scoreColor(score)
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded"
      style={{ backgroundColor: color + '22', color }}
      title={`Website-Score ${score}/100 · ${ratingLabel(rating)}`}>
      🌐 {score}{hasCritical ? ' ⚠' : ''}{!compact && rating ? ` · ${ratingLabel(rating)}` : ''}
    </span>
  )
}
