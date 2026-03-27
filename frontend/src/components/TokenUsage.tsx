import { useEffect, useState, useMemo } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'
import axios from 'axios'
import { formatDate, formatCurrency } from '../utils/formatters'
import type { TokenTrackerData } from '../types'

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend, Filler)

const CHART_COLORS = {
  accent: '#58a6ff',
  accentAlpha: 'rgba(88, 166, 255, 0.15)',
  green: '#3fb950',
  greenAlpha: 'rgba(63, 185, 80, 0.15)',
  orange: '#d29922',
  orangeAlpha: 'rgba(210, 153, 34, 0.15)',
  purple: '#bc8cff',
  red: '#f85149',
  border: '#30363d',
  surface: '#161b22',
  text: '#e6edf3',
  muted: '#8b949e',
}

const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#161b22',
      borderColor: '#30363d',
      borderWidth: 1,
      titleColor: '#e6edf3',
      bodyColor: '#8b949e',
      padding: 12,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: { color: 'rgba(48, 54, 61, 0.5)' },
      ticks: { color: '#8b949e', font: { size: 11 } },
    },
    y: {
      grid: { color: 'rgba(48, 54, 61, 0.5)' },
      ticks: { color: '#8b949e', font: { size: 11 } },
      beginAtZero: true,
    },
  },
}

type Period = '7d' | '30d' | '90d' | 'all' | 'custom'

interface Props {
  trackerUrl: string
}

function formatDateISO(d: Date): string {
  return d.toISOString().split('T')[0]
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} Min.`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h} Std. ${m} Min.` : `${h} Std.`
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} Mio.`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return n.toLocaleString('de-DE')
}

export default function TokenUsage({ trackerUrl }: Props) {
  const [data, setData] = useState<TokenTrackerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [period, setPeriod] = useState<Period>('all')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')

  const { from, to } = useMemo(() => {
    if (period === 'custom') return { from: customFrom, to: customTo }
    if (period === 'all') return { from: '', to: '' }
    const now = new Date()
    const days = period === '7d' ? 7 : period === '30d' ? 30 : 90
    const start = new Date(now.getTime() - days * 86400000)
    return { from: formatDateISO(start), to: formatDateISO(now) }
  }, [period, customFrom, customTo])

  useEffect(() => {
    if (!trackerUrl) return
    setLoading(true)
    setError(false)
    const params = new URLSearchParams()
    if (from) params.set('from', from)
    if (to) params.set('to', to)
    const sep = trackerUrl.includes('?') ? '&' : '?'
    const url = params.toString() ? `${trackerUrl}${sep}${params}` : trackerUrl
    axios.get<TokenTrackerData>(url)
      .then(res => setData(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [trackerUrl, from, to])

  if (loading) return <div className="text-text-muted py-12 text-center">KI-Nutzungsdaten werden geladen...</div>
  if (error || !data) return <div className="text-text-muted py-12 text-center">Daten konnten nicht geladen werden.</div>

  const s = data.summary
  const costEur = s.total_cost * 0.92 // USD to EUR approximation

  return (
    <div className="space-y-6">
      {/* Period Filter */}
      <div className="flex flex-wrap items-center gap-2">
        {(['7d', '30d', '90d', 'all'] as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 text-xs rounded-[6px] transition-all ${
              period === p
                ? 'bg-accent text-white'
                : 'bg-surface-2 text-text-muted border border-border hover:text-text hover:border-accent'
            }`}
          >
            {p === '7d' ? '7 Tage' : p === '30d' ? '30 Tage' : p === '90d' ? '90 Tage' : 'Gesamt'}
          </button>
        ))}
        <button
          onClick={() => setPeriod('custom')}
          className={`px-3 py-1.5 text-xs rounded-[6px] transition-all ${
            period === 'custom'
              ? 'bg-accent text-white'
              : 'bg-surface-2 text-text-muted border border-border hover:text-text hover:border-accent'
          }`}
        >
          Zeitraum
        </button>
        {period === 'custom' && (
          <div className="flex items-center gap-2 ml-2">
            <input type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)} className="!py-1 !px-2 !text-xs" />
            <span className="text-text-muted text-xs">bis</span>
            <input type="date" value={customTo} onChange={e => setCustomTo(e.target.value)} className="!py-1 !px-2 !text-xs" />
          </div>
        )}
      </div>

      {/* Explanatory Intro */}
      <div className="bg-surface border border-border rounded-[12px] p-4">
        <p className="text-sm text-text-muted">
          Diese Übersicht zeigt transparent, wann und wie intensiv KI-gestützte Entwicklungsarbeit an Ihrem Projekt stattgefunden hat.
          Jede Arbeitssitzung wird automatisch protokolliert — inkl. geschriebener Codezeilen, Dauer und eingesetzter KI-Modelle.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <p className="text-xs uppercase tracking-wider text-text-muted mb-2">KI-Kosten (ca.)</p>
          <p className="text-[28px] font-bold tabular-nums text-accent">{formatCurrency(costEur)}</p>
          <p className="text-xs text-text-muted mt-1">${s.total_cost.toFixed(2)} USD</p>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Arbeitssitzungen</p>
          <p className="text-[28px] font-bold tabular-nums text-success">{s.total_sessions}</p>
          <p className="text-xs text-text-muted mt-1">{formatDuration(s.total_duration_min)} Gesamtdauer</p>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <p className="text-xs uppercase tracking-wider text-text-muted mb-2">Codezeilen geschrieben</p>
          <p className="text-[28px] font-bold tabular-nums text-purple">{s.lines_written.toLocaleString('de-DE')}</p>
          <p className="text-xs text-text-muted mt-1">+{s.lines_added.toLocaleString('de-DE')} / −{s.lines_removed.toLocaleString('de-DE')}</p>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <p className="text-xs uppercase tracking-wider text-text-muted mb-2">KI-Anfragen</p>
          <p className="text-[28px] font-bold tabular-nums text-warning">{s.total_messages.toLocaleString('de-DE')}</p>
          <p className="text-xs text-text-muted mt-1">Einzelne Interaktionen mit der KI</p>
        </div>
      </div>

      {/* Daily Activity Chart */}
      {data.daily.length > 0 && (
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h4 className="text-sm font-semibold text-text mb-1">Arbeitsintensität pro Tag</h4>
          <p className="text-xs text-text-muted mb-4">Zeigt die Anzahl der KI-Anfragen und geschriebenen Codezeilen pro Arbeitstag.</p>
          <div style={{ height: 280 }}>
            <Bar
              data={{
                labels: data.daily.map(d => {
                  const date = new Date(d.date)
                  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
                }),
                datasets: [
                  {
                    label: 'KI-Anfragen',
                    data: data.daily.map(d => d.messages),
                    backgroundColor: CHART_COLORS.accentAlpha,
                    borderColor: CHART_COLORS.accent,
                    borderWidth: 1,
                    borderRadius: 4,
                  },
                ],
              }}
              options={{
                ...CHART_OPTIONS,
                plugins: {
                  ...CHART_OPTIONS.plugins,
                  tooltip: {
                    ...CHART_OPTIONS.plugins.tooltip,
                    callbacks: {
                      afterBody: (items) => {
                        const idx = items[0]?.dataIndex
                        if (idx === undefined) return ''
                        const d = data.daily[idx]
                        return [
                          `Codezeilen: ${d.lines_written}`,
                          `Kosten: $${d.cost.toFixed(2)}`,
                        ]
                      },
                    },
                  },
                },
              }}
            />
          </div>
        </div>
      )}

      {/* Cost Trend Chart */}
      {data.daily.length > 1 && (
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h4 className="text-sm font-semibold text-text mb-1">Kostenverlauf</h4>
          <p className="text-xs text-text-muted mb-4">Kumulierte KI-Kosten über den gewählten Zeitraum.</p>
          <div style={{ height: 220 }}>
            <Line
              data={{
                labels: data.daily.map(d => {
                  const date = new Date(d.date)
                  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
                }),
                datasets: [
                  {
                    label: 'Kosten kumuliert ($)',
                    data: data.daily.reduce<number[]>((acc, d) => {
                      const prev = acc.length > 0 ? acc[acc.length - 1] : 0
                      acc.push(prev + d.cost)
                      return acc
                    }, []),
                    borderColor: CHART_COLORS.green,
                    backgroundColor: CHART_COLORS.greenAlpha,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    borderWidth: 2,
                  },
                ],
              }}
              options={{
                ...CHART_OPTIONS,
                scales: {
                  ...CHART_OPTIONS.scales,
                  y: {
                    ...CHART_OPTIONS.scales.y,
                    ticks: {
                      ...CHART_OPTIONS.scales.y.ticks,
                      callback: (v) => `$${Number(v).toFixed(0)}`,
                    },
                  },
                },
              }}
            />
          </div>
        </div>
      )}

      {/* Code Output Chart */}
      {data.daily.length > 0 && data.daily.some(d => d.lines_written > 0) && (
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h4 className="text-sm font-semibold text-text mb-1">Code-Entwicklung pro Tag</h4>
          <p className="text-xs text-text-muted mb-4">Geschriebene, hinzugefügte und entfernte Codezeilen — zeigt den Entwicklungsfortschritt.</p>
          <div style={{ height: 220 }}>
            <Bar
              data={{
                labels: data.daily.map(d => {
                  const date = new Date(d.date)
                  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
                }),
                datasets: [
                  {
                    label: 'Geschrieben',
                    data: data.daily.map(d => d.lines_written),
                    backgroundColor: CHART_COLORS.purple,
                    borderRadius: 3,
                  },
                  {
                    label: 'Hinzugefügt',
                    data: data.daily.map(d => d.lines_added),
                    backgroundColor: CHART_COLORS.green,
                    borderRadius: 3,
                  },
                ],
              }}
              options={{
                ...CHART_OPTIONS,
                plugins: {
                  ...CHART_OPTIONS.plugins,
                  legend: { display: true, labels: { color: CHART_COLORS.muted, font: { size: 11 }, boxWidth: 12, padding: 16 } },
                },
              }}
            />
          </div>
        </div>
      )}

      {/* Sessions Timeline */}
      {data.sessions.length > 0 && (
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h4 className="text-sm font-semibold text-text mb-1">Arbeitssitzungen</h4>
          <p className="text-xs text-text-muted mb-4">Jede Sitzung entspricht einer zusammenhängenden Arbeitsphase am Projekt.</p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">Datum</th>
                  <th className="text-left text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">Dauer</th>
                  <th className="text-left text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">KI-Modell</th>
                  <th className="text-right text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">Anfragen</th>
                  <th className="text-right text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">Codezeilen</th>
                  <th className="text-right text-[11px] uppercase tracking-wider text-text-muted py-2.5 px-3">Kosten</th>
                </tr>
              </thead>
              <tbody>
                {data.sessions.map((session, i) => (
                  <tr key={i} className="border-b border-border hover:bg-surface-2 transition-colors">
                    <td className="py-2.5 px-3 text-[13px] text-text">{formatDate(session.start)}</td>
                    <td className="py-2.5 px-3 text-[13px] text-text-muted">{formatDuration(session.duration_min)}</td>
                    <td className="py-2.5 px-3 text-[13px] text-text-muted">{session.model}</td>
                    <td className="py-2.5 px-3 text-[13px] text-text tabular-nums text-right">{session.messages}</td>
                    <td className="py-2.5 px-3 text-[13px] tabular-nums text-right">
                      <span className="text-success">+{session.lines_added}</span>
                      {session.lines_removed > 0 && <span className="text-danger ml-1">−{session.lines_removed}</span>}
                    </td>
                    <td className="py-2.5 px-3 text-[13px] text-text tabular-nums text-right">${session.cost.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Models Used + Activity Range */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {s.models_used.length > 0 && (
          <div className="bg-surface border border-border rounded-[12px] p-5">
            <h4 className="text-sm font-semibold text-text mb-1">Eingesetzte KI-Modelle</h4>
            <p className="text-xs text-text-muted mb-3">Verschiedene Modelle werden je nach Aufgabe eingesetzt.</p>
            <div className="space-y-2">
              {s.models_used.filter(m => m.name !== 'System' && m.name !== 'Unknown').map((m) => (
                <div key={m.name} className="flex justify-between items-center py-1.5 px-3 bg-surface-2 rounded-lg">
                  <span className="text-sm text-text">{m.name}</span>
                  <div className="flex gap-4 text-xs text-text-muted tabular-nums">
                    <span>{m.messages} Anfragen</span>
                    <span>${m.cost.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h4 className="text-sm font-semibold text-text mb-1">Zusammenfassung</h4>
          <p className="text-xs text-text-muted mb-3">Eckdaten des Projekts im gewählten Zeitraum.</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-muted">Erster Einsatz</span>
              <span className="text-text">{s.first_activity ? formatDate(s.first_activity) : '–'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-muted">Letzter Einsatz</span>
              <span className="text-text">{s.last_activity ? formatDate(s.last_activity) : '–'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-muted">Gesamtdauer</span>
              <span className="text-text">{formatDuration(s.total_duration_min)}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-muted">KI-Anfragen gesamt</span>
              <span className="text-text tabular-nums">{s.total_messages.toLocaleString('de-DE')}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-text-muted">Gesamtkosten</span>
              <span className="text-accent font-semibold tabular-nums">{formatCurrency(costEur)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
