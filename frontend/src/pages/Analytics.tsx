import { useEffect, useState, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import {
  getProfitability,
  getForecast,
  type CustomerProfitability,
  type ForecastData,
} from '../api/analytics'
import { formatCurrency } from '../utils/formatters'
import toast from 'react-hot-toast'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const COLORS = {
  green: '#3fb950',
  orange: '#d29922',
  red: '#f85149',
  accent: '#58a6ff',
  border: '#30363d',
  textMuted: '#8b949e',
}

type SortKey = 'customer_name' | 'revenue' | 'hours_logged' | 'effective_hourly_rate' | 'invoices_count' | 'profit'

export default function Analytics() {
  const [profitability, setProfitability] = useState<CustomerProfitability[]>([])
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('revenue')
  const [sortAsc, setSortAsc] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [prof, fore] = await Promise.all([getProfitability(), getForecast()])
      setProfitability(prof)
      setForecast(fore)
    } catch {
      toast.error('Fehler beim Laden der Analyse-Daten.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  const sorted = [...profitability].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const maxRevenue = profitability.length > 0
    ? Math.max(...profitability.map((p) => p.revenue))
    : 1

  const rateColor = (rate: number) => {
    if (rate >= 100) return COLORS.green
    if (rate >= 50) return COLORS.orange
    return COLORS.red
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ''
    return sortAsc ? ' \u2191' : ' \u2193'
  }

  if (loading || !forecast) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  const forecastChartData = {
    labels: ['3 Monate', '6 Monate', '12 Monate'],
    datasets: [
      {
        label: 'Wiederkehrend',
        data: [
          forecast.monthly_recurring * 3,
          forecast.monthly_recurring * 6,
          forecast.monthly_recurring * 12,
        ],
        backgroundColor: COLORS.green,
        borderRadius: 4,
        barPercentage: 0.6,
        categoryPercentage: 0.5,
      },
      {
        label: 'Pipeline (gewichtet)',
        data: [
          forecast.pipeline_value * 0.3,
          forecast.pipeline_value * 0.5,
          forecast.pipeline_value * 0.7,
        ],
        backgroundColor: COLORS.orange,
        borderRadius: 4,
        barPercentage: 0.6,
        categoryPercentage: 0.5,
      },
    ],
  }

  const forecastChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: COLORS.textMuted, usePointStyle: true, pointStyle: 'circle' as const },
      },
      tooltip: {
        backgroundColor: '#1c2128',
        borderColor: COLORS.border,
        borderWidth: 1,
        titleColor: '#e6edf3',
        bodyColor: '#e6edf3',
        callbacks: {
          label: (ctx: { dataset: { label?: string }; parsed: { y: number } }) =>
            `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`,
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        grid: { color: COLORS.border, drawBorder: false },
        ticks: { color: COLORS.textMuted },
      },
      y: {
        stacked: true,
        grid: { color: COLORS.border, drawBorder: false },
        ticks: {
          color: COLORS.textMuted,
          callback: (value: string | number) => formatCurrency(Number(value)),
        },
      },
    },
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
        <h2 className="text-lg font-semibold text-text">Analyse</h2>
      </div>

      {/* Forecast KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Monatlich wiederkehrend
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: COLORS.green }}>
            {formatCurrency(forecast.monthly_recurring)}
          </div>
          <div className="text-xs text-text-muted mt-1">
            {formatCurrency(forecast.annual_recurring)} / Jahr
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Pipeline (Angebote)
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: COLORS.orange }}>
            {formatCurrency(forecast.pipeline_value)}
          </div>
          <div className="text-xs text-text-muted mt-1">
            {forecast.pipeline_count} offene Angebote
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Prognose 6 Monate
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: COLORS.accent }}>
            {formatCurrency(forecast.forecast_6m)}
          </div>
          <div className="text-xs text-text-muted mt-1">
            Wiederkehrend + Pipeline
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Leads in Bearbeitung
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: COLORS.accent }}>
            {forecast.leads_count}
          </div>
          <div className="text-xs text-text-muted mt-1">
            Neu oder kontaktiert
          </div>
        </div>
      </div>

      {/* Customer Profitability Table */}
      <div className="bg-surface border border-border rounded-[12px] overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-medium text-text">Kunden-Profitabilit\u00e4t</h3>
        </div>
        {sorted.length === 0 ? (
          <div className="px-5 py-8 text-center text-text-muted text-sm">
            Keine Kundendaten vorhanden.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-left">
                <th
                  className="px-5 py-2.5 font-medium cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('customer_name')}
                >
                  Kunde{sortIcon('customer_name')}
                </th>
                <th
                  className="px-5 py-2.5 font-medium text-right cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('revenue')}
                >
                  Umsatz{sortIcon('revenue')}
                </th>
                <th
                  className="px-5 py-2.5 font-medium text-right cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('hours_logged')}
                >
                  Stunden{sortIcon('hours_logged')}
                </th>
                <th
                  className="px-5 py-2.5 font-medium text-right cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('effective_hourly_rate')}
                >
                  Eff. Stundensatz{sortIcon('effective_hourly_rate')}
                </th>
                <th
                  className="px-5 py-2.5 font-medium text-right cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('invoices_count')}
                >
                  Rechnungen{sortIcon('invoices_count')}
                </th>
                <th
                  className="px-5 py-2.5 font-medium text-right cursor-pointer hover:text-text select-none"
                  onClick={() => handleSort('profit')}
                >
                  Gewinn{sortIcon('profit')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.customer_id}
                  className="border-b border-border hover:bg-surface-2 transition-colors"
                >
                  <td className="px-5 py-2.5 text-text">
                    <div>{row.customer_name}</div>
                    {/* Revenue bar indicator */}
                    <div className="w-full h-1 rounded-full bg-surface-2 overflow-hidden mt-1">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(row.revenue / maxRevenue) * 100}%`,
                          backgroundColor: COLORS.accent,
                        }}
                      />
                    </div>
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums" style={{ color: COLORS.green }}>
                    {formatCurrency(row.revenue)}
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums text-text">
                    {row.hours_logged > 0 ? row.hours_logged.toFixed(1) + ' h' : '\u2014'}
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums">
                    <span
                      className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                      style={{
                        color: rateColor(row.effective_hourly_rate),
                        backgroundColor: rateColor(row.effective_hourly_rate) + '20',
                      }}
                    >
                      {row.effective_hourly_rate > 0
                        ? formatCurrency(row.effective_hourly_rate)
                        : '\u2014'}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums text-text">
                    {row.invoices_count}
                  </td>
                  <td
                    className="px-5 py-2.5 text-right tabular-nums"
                    style={{ color: row.profit >= 0 ? COLORS.green : COLORS.red }}
                  >
                    {formatCurrency(row.profit)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Forecast Chart */}
      <div className="bg-surface border border-border rounded-[12px] p-5">
        <h3 className="text-sm font-medium text-text mb-4">Umsatzprognose</h3>
        <div style={{ height: '300px' }}>
          <Bar data={forecastChartData} options={forecastChartOptions as any} />
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <div className="text-xs text-text-muted mb-1">3 Monate</div>
            <div className="text-sm font-semibold tabular-nums text-text">
              {formatCurrency(forecast.forecast_3m)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-text-muted mb-1">6 Monate</div>
            <div className="text-sm font-semibold tabular-nums text-text">
              {formatCurrency(forecast.forecast_6m)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-text-muted mb-1">12 Monate</div>
            <div className="text-sm font-semibold tabular-nums text-text">
              {formatCurrency(forecast.forecast_12m)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
