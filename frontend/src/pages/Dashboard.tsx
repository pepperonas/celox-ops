import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DashboardStats } from '../types'
import { formatCurrency } from '../utils/formatters'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get('/dashboard/stats')
      .then((res) => setStats(res.data))
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

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Dashboard</h2>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-surface border border-border rounded-[12px] p-5 animate-pulse">
              <div className="h-3 bg-surface-2 rounded w-1/2 mb-3" />
              <div className="h-7 bg-surface-2 rounded w-2/3 mb-2" />
              <div className="h-3 bg-surface-2 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          {cards.map((card) => (
            <div key={card.label} className="bg-surface border border-border rounded-[12px] p-5">
              <p className="text-xs uppercase tracking-wider text-text-muted mb-2">{card.label}</p>
              <p className={`text-[28px] font-bold tabular-nums ${card.valueColor}`}>{card.value}</p>
              <p className="text-xs text-text-muted mt-1">{card.sub}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
