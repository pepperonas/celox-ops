import { useEffect, useState } from 'react'
import '../../utils/charts'
import { Bar } from 'react-chartjs-2'
import PageHeader from '../../components/PageHeader'
import LoadingIndicator from '../../components/LoadingIndicator'
import RainmakerNav from './RainmakerNav'
import { getRainmakerStats } from '../../api/rainmaker'
import { formatCurrency } from '../../utils/formatters'
import type { RainmakerStats } from '../../types'
import { ACTIVITY_TYPE_LABELS, STATUS_LABELS, STATUS_COLORS } from './constants'

const C = { accent: '#7cb0ff', muted: '#9aa6b5', border: '#2c333d', surface: '#1a2028', text: '#e3e7ee' }

const baseChartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { backgroundColor: C.surface, borderColor: C.border, borderWidth: 1, titleColor: C.text, bodyColor: C.muted } },
  scales: {
    x: { grid: { color: C.border }, border: { display: false }, ticks: { color: C.muted, font: { size: 11 } } },
    y: { grid: { color: C.border }, border: { display: false }, ticks: { color: C.muted, font: { size: 11 }, precision: 0 }, beginAtZero: true },
  },
} as const

export default function RainmakerStatistics() {
  const [stats, setStats] = useState<RainmakerStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRainmakerStats().then(setStats).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading || !stats) {
    return (
      <div>
        <PageHeader title="Statistik" />
        <RainmakerNav />
        <LoadingIndicator />
      </div>
    )
  }

  const maxFunnel = Math.max(1, ...stats.funnel.map((f) => f.count))
  const kpis = [
    { label: 'Leads gesamt', value: String(stats.total_leads), color: 'text-text' },
    { label: 'Gewonnen', value: String(stats.won_count), color: 'text-success' },
    { label: 'Offenes Volumen', value: formatCurrency(stats.open_value || 0), color: 'text-accent' },
    { label: 'Punkte', value: String(stats.total_points), color: 'text-purple' },
  ]

  return (
    <div>
      <PageHeader title="Statistik" subtitle="Aktivität wird belohnt, nicht nur Abschlüsse" />
      <RainmakerNav />

      {/* KPI tiles */}
      <div className="md-stagger grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpis.map((k) => (
          <div key={k.label} className="bg-surface-container border border-border rounded-md p-5 hover:shadow-elev-2 transition-all duration-medium ease-spring hover:-translate-y-0.5">
            <p className="text-xs text-text-muted mb-2">{k.label}</p>
            <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Activity per day */}
        <div className="card">
          <h3 className="text-sm font-semibold text-text mb-4">Aktivitäten (14 Tage)</h3>
          <div style={{ height: 240 }}>
            <Bar
              data={{
                labels: stats.activity_by_day.map((d) => d.date.slice(8, 10) + '.' + d.date.slice(5, 7)),
                datasets: [{ data: stats.activity_by_day.map((d) => d.count), backgroundColor: C.accent, borderRadius: 4, barPercentage: 0.7 }],
              }}
              options={baseChartOpts as never}
            />
          </div>
        </div>

        {/* Activity by type */}
        <div className="card">
          <h3 className="text-sm font-semibold text-text mb-4">Nach Typ (30 Tage)</h3>
          <div style={{ height: 240 }}>
            {stats.activity_by_type.length === 0 ? (
              <p className="text-text-muted text-sm">Noch keine erledigten Aktivitäten.</p>
            ) : (
              <Bar
                data={{
                  labels: stats.activity_by_type.map((t) => ACTIVITY_TYPE_LABELS[t.type]),
                  datasets: [{ data: stats.activity_by_type.map((t) => t.count), backgroundColor: '#a371f7', borderRadius: 4, barPercentage: 0.6 }],
                }}
                options={{ ...baseChartOpts, indexAxis: 'y' } as never}
              />
            )}
          </div>
        </div>
      </div>

      {/* Conversion funnel */}
      <div className="card">
        <h3 className="text-sm font-semibold text-text mb-4">Conversion-Funnel</h3>
        <div className="space-y-3">
          {stats.funnel.map((f) => {
            const color = STATUS_COLORS[f.status]
            return (
              <div key={f.status} className="flex items-center gap-3">
                <span className="text-xs text-text-muted w-28 shrink-0">{STATUS_LABELS[f.status]}</span>
                <div className="flex-1 h-7 rounded-lg bg-surface-high overflow-hidden">
                  <div className="h-full rounded-lg flex items-center justify-end px-2 transition-all duration-long ease-emphasized" style={{ width: `${Math.max((f.count / maxFunnel) * 100, f.count > 0 ? 8 : 0)}%`, backgroundColor: color + '40', borderRight: f.count > 0 ? `3px solid ${color}` : 'none' }}>
                    {f.count > 0 && <span className="text-xs font-semibold" style={{ color }}>{f.count}</span>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

    </div>
  )
}
