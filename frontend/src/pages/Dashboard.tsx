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
          value: formatCurrency(stats.umsatz_monat),
          sub: `Jahr: ${formatCurrency(stats.umsatz_jahr)}`,
          color: 'text-celox-400',
          bg: 'bg-celox-500/10 border-celox-500/20',
        },
        {
          label: 'Offene Rechnungen',
          value: String(stats.offene_rechnungen_anzahl),
          sub: formatCurrency(stats.offene_rechnungen_summe),
          color: 'text-blue-400',
          bg: 'bg-blue-500/10 border-blue-500/20',
        },
        {
          label: 'Ueberfaellige Rechnungen',
          value: String(stats.ueberfaellige_rechnungen_anzahl),
          sub: formatCurrency(stats.ueberfaellige_rechnungen_summe),
          color: 'text-red-400',
          bg: 'bg-red-500/10 border-red-500/20',
        },
        {
          label: 'Aktive Vertraege',
          value: String(stats.aktive_vertraege_anzahl),
          sub: `${formatCurrency(stats.aktive_vertraege_monatlich)} / Monat`,
          color: 'text-green-400',
          bg: 'bg-green-500/10 border-green-500/20',
        },
      ]
    : []

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-100 mb-6">Dashboard</h2>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-gray-800 rounded w-1/2 mb-3" />
              <div className="h-8 bg-gray-800 rounded w-2/3 mb-2" />
              <div className="h-3 bg-gray-800 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {cards.map((card) => (
            <div key={card.label} className={`rounded-xl border p-6 ${card.bg}`}>
              <p className="text-sm font-medium text-gray-400 mb-1">{card.label}</p>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
              <p className="text-sm text-gray-500 mt-1">{card.sub}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
