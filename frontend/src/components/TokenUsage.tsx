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

  const exportHTML = () => {
    const label = data.label || 'Projekt'
    const periodLabel = from && to ? `${from} bis ${to}` : from ? `ab ${from}` : to ? `bis ${to}` : 'Gesamter Zeitraum'
    const models = s.models_used.filter(m => m.name !== 'System' && m.name !== 'Unknown')

    const html = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KI-Nutzungsbericht — ${label}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 14px; color: #1a1a2e; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 40px 24px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { font-size: 16px; margin: 32px 0 12px; color: #1a1a2e; border-bottom: 2px solid #e8e8e8; padding-bottom: 6px; }
  .subtitle { color: #666; font-size: 13px; margin-bottom: 24px; }
  .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; border-bottom: 3px solid #58a6ff; padding-bottom: 16px; }
  .brand { font-size: 18px; font-weight: 700; color: #58a6ff; }
  .brand-sub { font-size: 11px; color: #999; }
  .date { font-size: 12px; color: #999; text-align: right; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
  .kpi { background: #f8f9fa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; }
  .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin-bottom: 4px; }
  .kpi-value { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .kpi-sub { font-size: 11px; color: #999; margin-top: 2px; }
  .blue { color: #58a6ff; } .green { color: #22863a; } .purple { color: #8957e5; } .orange { color: #d29922; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
  th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; border-bottom: 2px solid #e8e8e8; padding: 8px 10px; }
  td { padding: 8px 10px; border-bottom: 1px solid #f0f0f0; }
  tr:hover td { background: #f8f9fa; }
  .right { text-align: right; }
  .mono { font-variant-numeric: tabular-nums; }
  .badge { display: inline-block; background: #f0f4ff; color: #58a6ff; border: 1px solid #d0e0ff; border-radius: 4px; padding: 2px 8px; font-size: 12px; margin: 2px; }
  .models { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
  .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .summary-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
  .summary-label { color: #666; }
  .summary-value { font-weight: 600; font-variant-numeric: tabular-nums; }
  .intro { background: #f8f9fa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px; color: #666; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e8e8e8; font-size: 11px; color: #999; text-align: center; }
  @media print { body { padding: 20px; } .kpis { grid-template-columns: repeat(4, 1fr); } }
  @media (max-width: 600px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="brand">celox.io</div>
    <div class="brand-sub">IT-Consulting</div>
  </div>
  <div class="date">Erstellt am ${new Date().toLocaleDateString('de-DE')}</div>
</div>

<h1>KI-Nutzungsbericht</h1>
<div class="subtitle">${label} — Zeitraum: ${periodLabel}</div>

<div class="intro">
  Dieser Bericht dokumentiert die KI-gestützte Entwicklungsarbeit an Ihrem Projekt.
  Jede Arbeitssitzung wird automatisch protokolliert — inklusive geschriebener Codezeilen,
  Dauer und eingesetzter KI-Modelle.
</div>

<div class="kpis">
  <div class="kpi">
    <div class="kpi-label">KI-Kosten</div>
    <div class="kpi-value blue">${formatCurrency(costEur)}</div>
    <div class="kpi-sub">$${s.total_cost.toFixed(2)} USD</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Arbeitssitzungen</div>
    <div class="kpi-value green">${s.total_sessions}</div>
    <div class="kpi-sub">${formatDuration(s.total_duration_min)} Gesamtdauer</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Codezeilen</div>
    <div class="kpi-value purple">${s.lines_written.toLocaleString('de-DE')}</div>
    <div class="kpi-sub">+${s.lines_added.toLocaleString('de-DE')} / −${s.lines_removed.toLocaleString('de-DE')}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">KI-Anfragen</div>
    <div class="kpi-value orange">${s.total_messages.toLocaleString('de-DE')}</div>
    <div class="kpi-sub">Einzelne Interaktionen</div>
  </div>
</div>

${models.length > 0 ? `
<h2>Eingesetzte KI-Modelle</h2>
<div class="models">
  ${models.map(m => `<span class="badge">${m.name} (${m.messages} Anfragen, $${m.cost.toFixed(2)})</span>`).join('')}
</div>
` : ''}

${data.sessions.length > 0 ? `
<h2>Arbeitssitzungen</h2>
<table>
  <thead>
    <tr><th>Datum</th><th>Dauer</th><th>KI-Modell</th><th class="right">Anfragen</th><th class="right">Codezeilen</th><th class="right">Kosten</th></tr>
  </thead>
  <tbody>
    ${data.sessions.map(ss => `<tr>
      <td>${ss.start ? new Date(ss.start).toLocaleDateString('de-DE') : '-'}</td>
      <td>${formatDuration(ss.duration_min)}</td>
      <td>${ss.model || '-'}</td>
      <td class="right mono">${ss.messages}</td>
      <td class="right mono"><span class="green">+${ss.lines_added}</span>${ss.lines_removed > 0 ? ` <span style="color:#d73a49">−${ss.lines_removed}</span>` : ''}</td>
      <td class="right mono">$${ss.cost.toFixed(2)}</td>
    </tr>`).join('')}
  </tbody>
</table>
` : ''}

${data.daily.filter(d => d.messages > 0).length > 0 ? `
<h2>Tagesübersicht</h2>
<table>
  <thead>
    <tr><th>Datum</th><th class="right">KI-Anfragen</th><th class="right">Codezeilen</th><th class="right">Kosten</th></tr>
  </thead>
  <tbody>
    ${data.daily.filter(d => d.messages > 0).map(d => `<tr>
      <td>${new Date(d.date).toLocaleDateString('de-DE')}</td>
      <td class="right mono">${d.messages}</td>
      <td class="right mono">${d.lines_written}</td>
      <td class="right mono">$${d.cost.toFixed(2)}</td>
    </tr>`).join('')}
  </tbody>
</table>
` : ''}

<h2>Zusammenfassung</h2>
<div class="summary-grid">
  <div>
    <div class="summary-item"><span class="summary-label">Erster Einsatz</span><span class="summary-value">${s.first_activity ? new Date(s.first_activity).toLocaleDateString('de-DE') : '–'}</span></div>
    <div class="summary-item"><span class="summary-label">Letzter Einsatz</span><span class="summary-value">${s.last_activity ? new Date(s.last_activity).toLocaleDateString('de-DE') : '–'}</span></div>
    <div class="summary-item"><span class="summary-label">Gesamtdauer</span><span class="summary-value">${formatDuration(s.total_duration_min)}</span></div>
  </div>
  <div>
    <div class="summary-item"><span class="summary-label">KI-Anfragen</span><span class="summary-value">${s.total_messages.toLocaleString('de-DE')}</span></div>
    <div class="summary-item"><span class="summary-label">Input-Tokens</span><span class="summary-value">${formatTokens(s.total_input_tokens)}</span></div>
    <div class="summary-item"><span class="summary-label">Output-Tokens</span><span class="summary-value">${formatTokens(s.total_output_tokens)}</span></div>
  </div>
</div>

<div class="footer">
  celox.io — IT-Consulting | Martin Pfeffer | Generiert aus dem celox.io Token Tracker
</div>

</body>
</html>`

    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ki-nutzungsbericht-${from || 'gesamt'}-${to || 'heute'}.html`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportCSV = () => {
    const header = 'Datum;KI-Anfragen;Codezeilen geschrieben;Zeilen hinzugefügt;Zeilen entfernt;Kosten (USD)\n'
    const rows = data.daily.map(d =>
      `${d.date};${d.messages};${d.lines_written};${d.lines_added};${d.lines_removed};${d.cost.toFixed(2)}`
    ).join('\n')
    const sessHeader = '\n\nArbeitssitzungen\nDatum;Dauer (Min);Modell;Anfragen;Geschrieben;Hinzugefügt;Entfernt;Kosten (USD)\n'
    const sessRows = data.sessions.map(ss =>
      `${ss.start?.split('T')[0] || ''};${Math.round(ss.duration_min)};${ss.model};${ss.messages};${ss.lines_written};${ss.lines_added};${ss.lines_removed};${ss.cost.toFixed(2)}`
    ).join('\n')
    const bom = '\uFEFF'
    const blob = new Blob([bom + header + rows + sessHeader + sessRows], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ki-nutzung-${from || 'gesamt'}-${to || 'heute'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Period Filter + Export */}
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
        <div className="ml-auto flex gap-2">
          <button onClick={exportHTML} className="btn-primary !text-xs !py-1.5 !px-3">
            HTML Bericht
          </button>
          <button onClick={exportCSV} className="btn-secondary !text-xs !py-1.5 !px-3">
            CSV Export
          </button>
        </div>
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
