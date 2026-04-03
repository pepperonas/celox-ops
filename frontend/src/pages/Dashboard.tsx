import { useEffect, useState } from 'react'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { api } from '../api/client'
import type { DashboardStats } from '../types'
import { formatCurrency } from '../utils/formatters'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

const colors = {
  background: '#0d1117',
  surface: '#161b22',
  border: '#30363d',
  text: '#e6edf3',
  muted: '#8b949e',
  accent: '#58a6ff',
  green: '#3fb950',
  red: '#f85149',
  orange: '#d29922',
  purple: '#bc8cff',
}

interface ChartData {
  revenue_by_month: { month: string; revenue: number; expenses: number }[]
  invoice_status_distribution: { status: string; count: number; total: number }[]
  top_customers: { name: string; revenue: number; invoices_count: number }[]
  recent_invoices: {
    invoice_number: string
    customer_name: string
    total: number
    status: string
    date: string
  }[]
  recent_activities: {
    type: string
    title: string
    customer_name: string
    created_at: string
  }[]
}

const statusColors: Record<string, string> = {
  entwurf: colors.muted,
  gestellt: colors.accent,
  bezahlt: colors.green,
  ueberfaellig: colors.red,
  storniert: '#484f58',
}

const statusLabels: Record<string, string> = {
  entwurf: 'Entwurf',
  gestellt: 'Gestellt',
  bezahlt: 'Bezahlt',
  ueberfaellig: 'Überfällig',
  storniert: 'Storniert',
}

const activityDotColors: Record<string, string> = {
  invoice: colors.green,
  order: colors.accent,
  contract: colors.purple,
  customer: colors.orange,
  expense: colors.red,
}

function formatMonthLabel(month: string): string {
  const [y, m] = month.split('-')
  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
  return `${months[parseInt(m) - 1]} ${y.slice(2)}`
}

function timeAgo(dateStr: string): string {
  const now = new Date()
  const d = new Date(dateStr)
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'gerade eben'
  if (diffMin < 60) return `vor ${diffMin} Min.`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `vor ${diffH} Std.`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 30) return `vor ${diffD} Tag${diffD > 1 ? 'en' : ''}`
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/dashboard/stats'),
      api.get('/dashboard/charts'),
    ])
      .then(([statsRes, chartsRes]) => {
        setStats(statsRes.data)
        setChartData(chartsRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const cards = stats
    ? [
        {
          label: 'Umsatz (Monat)',
          value: formatCurrency(stats.revenue_month),
          sub: `Jahr: ${formatCurrency(stats.revenue_year)}`,
          valueColor: 'text-accent',
        },
        {
          label: 'Umsatz (Jahr)',
          value: formatCurrency(stats.revenue_year),
          sub: `Monat: ${formatCurrency(stats.revenue_month)}`,
          valueColor: 'text-success',
        },
        {
          label: 'Entwürfe',
          value: String(stats.draft_invoices_count),
          sub: formatCurrency(stats.draft_invoices_sum),
          valueColor: 'text-text-muted',
        },
        {
          label: 'Offene Rechnungen',
          value: String(stats.open_invoices_count),
          sub: formatCurrency(stats.open_invoices_sum),
          valueColor: stats.overdue_invoices_count > 0 ? 'text-danger' : 'text-warning',
        },
        {
          label: 'Aktive Verträge',
          value: String(stats.active_contracts_count),
          sub: `${formatCurrency(stats.active_contracts_monthly_sum)} / Monat`,
          valueColor: 'text-purple',
        },
      ]
    : []

  const maxCustomerRevenue = chartData?.top_customers?.length
    ? Math.max(...chartData.top_customers.map((c) => c.revenue))
    : 1

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Dashboard</h2>
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-[12px] p-5 animate-pulse">
              <div className="h-3 bg-surface-2 rounded w-1/2 mb-3" />
              <div className="h-7 bg-surface-2 rounded w-2/3 mb-2" />
              <div className="h-3 bg-surface-2 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4 mb-6">
          {cards.map((card) => (
            <div key={card.label} className="bg-surface border border-border rounded-[12px] p-5">
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">{card.label}</p>
              <p className={`text-[28px] font-bold tabular-nums ${card.valueColor}`}>{card.value}</p>
              <p className="text-xs text-text-muted mt-1">{card.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* Charts Row */}
      {chartData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* Revenue & Expenses Bar Chart */}
          <div className="bg-surface border border-border rounded-[12px] p-5">
            <h3 className="text-sm font-semibold text-text mb-4">Umsatz & Ausgaben (12 Monate)</h3>
            <div style={{ height: 280 }}>
              <Bar
                data={{
                  labels: chartData.revenue_by_month.map((d) => formatMonthLabel(d.month)),
                  datasets: [
                    {
                      label: 'Umsatz',
                      data: chartData.revenue_by_month.map((d) => d.revenue),
                      backgroundColor: colors.green,
                      borderRadius: 4,
                      barPercentage: 0.7,
                      categoryPercentage: 0.8,
                    },
                    {
                      label: 'Ausgaben',
                      data: chartData.revenue_by_month.map((d) => d.expenses),
                      backgroundColor: colors.red,
                      borderRadius: 4,
                      barPercentage: 0.7,
                      categoryPercentage: 0.8,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: 'top',
                      labels: {
                        color: colors.muted,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 16,
                        font: { size: 12 },
                      },
                    },
                    tooltip: {
                      backgroundColor: colors.surface,
                      titleColor: colors.text,
                      bodyColor: colors.muted,
                      borderColor: colors.border,
                      borderWidth: 1,
                      callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.raw as number)}`,
                      },
                    },
                  },
                  scales: {
                    x: {
                      grid: { color: colors.border },
                      border: { display: false },
                      ticks: { color: colors.muted, font: { size: 11 } },
                    },
                    y: {
                      grid: { color: colors.border },
                      border: { display: false },
                      ticks: {
                        color: colors.muted,
                        font: { size: 11 },
                        callback: (v) => `${Number(v).toLocaleString('de-DE')} \u20AC`,
                      },
                    },
                  },
                }}
              />
            </div>
          </div>

          {/* Invoice Status Doughnut */}
          <div className="bg-surface border border-border rounded-[12px] p-5">
            <h3 className="text-sm font-semibold text-text mb-4">Rechnungsstatus-Verteilung</h3>
            <div className="flex items-center justify-center" style={{ height: 280 }}>
              <div style={{ width: 240, height: 240 }}>
                <Doughnut
                  data={{
                    labels: chartData.invoice_status_distribution.map(
                      (d) => statusLabels[d.status] || d.status
                    ),
                    datasets: [
                      {
                        data: chartData.invoice_status_distribution.map((d) => d.count),
                        backgroundColor: chartData.invoice_status_distribution.map(
                          (d) => statusColors[d.status] || colors.muted
                        ),
                        borderColor: colors.surface,
                        borderWidth: 2,
                      },
                    ],
                  }}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                      legend: {
                        position: 'right',
                        labels: {
                          color: colors.muted,
                          usePointStyle: true,
                          pointStyle: 'circle',
                          padding: 12,
                          font: { size: 12 },
                        },
                      },
                      tooltip: {
                        backgroundColor: colors.surface,
                        titleColor: colors.text,
                        bodyColor: colors.muted,
                        borderColor: colors.border,
                        borderWidth: 1,
                        callbacks: {
                          label: (ctx) => {
                            const item = chartData.invoice_status_distribution[ctx.dataIndex]
                            return `${ctx.label}: ${item.count} (${formatCurrency(item.total)})`
                          },
                        },
                      },
                    },
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Row: Top Customers + Recent Activities */}
      {chartData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Top 5 Customers */}
          <div className="bg-surface border border-border rounded-[12px] p-5">
            <h3 className="text-sm font-semibold text-text mb-4">Top 5 Kunden nach Umsatz</h3>
            {chartData.top_customers.length === 0 ? (
              <p className="text-text-muted text-sm">Keine Daten vorhanden</p>
            ) : (
              <div className="space-y-3">
                {chartData.top_customers.map((customer, idx) => (
                  <div key={customer.name} className="flex items-center gap-3">
                    <span className="text-text-muted text-xs font-mono w-5 text-right shrink-0">
                      {idx + 1}.
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline mb-1">
                        <span className="text-sm text-text truncate">{customer.name}</span>
                        <span className="text-sm font-semibold text-text tabular-nums ml-2 shrink-0">
                          {formatCurrency(customer.revenue)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${(customer.revenue / maxCustomerRevenue) * 100}%`,
                              backgroundColor: colors.accent,
                            }}
                          />
                        </div>
                        <span className="text-xs text-text-muted shrink-0">
                          {customer.invoices_count} Rechnung{customer.invoices_count !== 1 ? 'en' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Activities */}
          <div className="bg-surface border border-border rounded-[12px] p-5">
            <h3 className="text-sm font-semibold text-text mb-4">Letzte Aktivitäten</h3>
            {chartData.recent_activities.length === 0 ? (
              <p className="text-text-muted text-sm">Keine Aktivitäten vorhanden</p>
            ) : (
              <div className="space-y-3">
                {chartData.recent_activities.map((activity, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div
                      className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                      style={{
                        backgroundColor: activityDotColors[activity.type] || colors.muted,
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text truncate">{activity.title}</p>
                      <div className="flex justify-between items-center mt-0.5">
                        <span className="text-xs text-text-muted truncate">
                          {activity.customer_name}
                        </span>
                        <span className="text-xs text-text-muted shrink-0 ml-2">
                          {activity.created_at ? timeAgo(activity.created_at) : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
