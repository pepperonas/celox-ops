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
import { getEuerOverview, exportEuerCsv, downloadMonthlyReport, type EuerOverview } from '../api/euer'
import { formatCurrency } from '../utils/formatters'
import toast from 'react-hot-toast'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const CHART_COLORS = {
  green: '#3fb950',
  greenAlpha: 'rgba(63, 185, 80, 0.15)',
  red: '#f85149',
  redAlpha: 'rgba(248, 81, 73, 0.15)',
  accent: '#58a6ff',
  accentAlpha: 'rgba(88, 166, 255, 0.15)',
  border: '#30363d',
  surface: '#161b22',
  textMuted: '#8b949e',
}

const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

export default function Euer() {
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1
  const [year, setYear] = useState(currentYear)
  const [data, setData] = useState<EuerOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [reportMonth, setReportMonth] = useState(currentMonth)
  const [reportYear, setReportYear] = useState(currentYear)
  const [generatingReport, setGeneratingReport] = useState(false)

  const yearOptions = Array.from({ length: 4 }, (_, i) => currentYear - i)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getEuerOverview(year)
      setData(res)
    } catch {
      toast.error('Fehler beim Laden der EÜR-Daten.')
    }
    setLoading(false)
  }, [year])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleExport = async () => {
    try {
      await exportEuerCsv(year)
      toast.success('CSV-Export heruntergeladen.')
    } catch {
      toast.error('Fehler beim Export.')
    }
  }

  const handleMonthlyReport = async () => {
    setGeneratingReport(true)
    try {
      await downloadMonthlyReport(reportYear, reportMonth)
      toast.success('Monatsbericht heruntergeladen.')
    } catch {
      toast.error('Fehler beim Erstellen des Monatsberichts.')
    }
    setGeneratingReport(false)
  }

  if (loading || !data) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  const monthLabels = data.revenue_by_month.map((m) => m.label.substring(0, 3))

  const barChartData = {
    labels: monthLabels,
    datasets: [
      {
        label: 'Einnahmen',
        data: data.revenue_by_month.map((m) => m.amount),
        backgroundColor: CHART_COLORS.green,
        borderRadius: 4,
        barPercentage: 0.7,
        categoryPercentage: 0.6,
      },
      {
        label: 'Ausgaben',
        data: data.expenses_by_month.map((m) => m.amount),
        backgroundColor: CHART_COLORS.red,
        borderRadius: 4,
        barPercentage: 0.7,
        categoryPercentage: 0.6,
      },
    ],
  }

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: CHART_COLORS.textMuted, usePointStyle: true, pointStyle: 'circle' as const },
      },
      tooltip: {
        backgroundColor: '#1c2128',
        borderColor: CHART_COLORS.border,
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
        grid: { color: CHART_COLORS.border, drawBorder: false },
        ticks: { color: CHART_COLORS.textMuted },
      },
      y: {
        grid: { color: CHART_COLORS.border, drawBorder: false },
        ticks: {
          color: CHART_COLORS.textMuted,
          callback: (value: string | number) => formatCurrency(Number(value)),
        },
      },
    },
  }

  // Find max category amount for horizontal bar widths
  const maxCatAmount = data.expenses_by_category.length > 0
    ? Math.max(...data.expenses_by_category.map((c) => c.amount))
    : 1

  return (
    <div>
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
        <h2 className="text-lg font-semibold text-text">
          Einnahmen-Überschuss-Rechnung
        </h2>
        <div className="flex items-center gap-3">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="input-field w-auto"
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <button onClick={handleExport} className="btn-secondary flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            CSV Export
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Einnahmen
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: CHART_COLORS.green }}>
            {formatCurrency(data.revenue_total)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Ausgaben
          </div>
          <div className="text-xl font-semibold tabular-nums" style={{ color: CHART_COLORS.red }}>
            {formatCurrency(data.expenses_total)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Gewinn
          </div>
          <div
            className="text-xl font-semibold tabular-nums"
            style={{ color: data.profit >= 0 ? CHART_COLORS.accent : CHART_COLORS.red }}
          >
            {formatCurrency(data.profit)}
          </div>
        </div>
      </div>

      {/* Monthly Bar Chart */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mb-6">
        <h3 className="text-sm font-medium text-text mb-4">Monatsübersicht</h3>
        <div style={{ height: '300px' }}>
          <Bar data={barChartData} options={barChartOptions as any} />
        </div>
      </div>

      {/* Quarterly Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {data.quarterly.map((q) => (
          <div
            key={q.quarter}
            className="bg-surface border border-border rounded-[12px] p-4"
          >
            <div className="text-xs uppercase tracking-wider text-text-muted mb-3">
              {q.label}
            </div>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Einnahmen</span>
                <span className="tabular-nums" style={{ color: CHART_COLORS.green }}>
                  {formatCurrency(q.revenue)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Ausgaben</span>
                <span className="tabular-nums" style={{ color: CHART_COLORS.red }}>
                  {formatCurrency(q.expenses)}
                </span>
              </div>
              <div className="flex justify-between pt-1.5 border-t border-border">
                <span className="text-text-muted font-medium">Gewinn</span>
                <span
                  className="tabular-nums font-medium"
                  style={{ color: q.profit >= 0 ? CHART_COLORS.accent : CHART_COLORS.red }}
                >
                  {formatCurrency(q.profit)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Monthly Table */}
      <div className="bg-surface border border-border rounded-[12px] overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-medium text-text">Monatliche Aufstellung</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-muted text-left">
              <th className="px-5 py-2.5 font-medium">Monat</th>
              <th className="px-5 py-2.5 font-medium text-right">Einnahmen</th>
              <th className="px-5 py-2.5 font-medium text-right">Ausgaben</th>
              <th className="px-5 py-2.5 font-medium text-right">Gewinn</th>
            </tr>
          </thead>
          <tbody>
            {data.revenue_by_month.map((rev, i) => {
              const exp = data.expenses_by_month[i].amount
              const profit = rev.amount - exp
              return (
                <tr key={rev.month} className="border-b border-border hover:bg-surface-2 transition-colors">
                  <td className="px-5 py-2.5 text-text">{rev.label}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums" style={{ color: CHART_COLORS.green }}>
                    {formatCurrency(rev.amount)}
                  </td>
                  <td className="px-5 py-2.5 text-right tabular-nums" style={{ color: CHART_COLORS.red }}>
                    {formatCurrency(exp)}
                  </td>
                  <td
                    className="px-5 py-2.5 text-right tabular-nums"
                    style={{ color: profit >= 0 ? CHART_COLORS.green : CHART_COLORS.red }}
                  >
                    {formatCurrency(profit)}
                  </td>
                </tr>
              )
            })}
            {/* Totals row */}
            <tr className="bg-surface-2 font-semibold">
              <td className="px-5 py-2.5 text-text">Gesamt</td>
              <td className="px-5 py-2.5 text-right tabular-nums" style={{ color: CHART_COLORS.green }}>
                {formatCurrency(data.revenue_total)}
              </td>
              <td className="px-5 py-2.5 text-right tabular-nums" style={{ color: CHART_COLORS.red }}>
                {formatCurrency(data.expenses_total)}
              </td>
              <td
                className="px-5 py-2.5 text-right tabular-nums"
                style={{ color: data.profit >= 0 ? CHART_COLORS.green : CHART_COLORS.red }}
              >
                {formatCurrency(data.profit)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Expenses by Category */}
      {data.expenses_by_category.length > 0 && (
        <div className="bg-surface border border-border rounded-[12px] p-5">
          <h3 className="text-sm font-medium text-text mb-4">Ausgaben nach Kategorie</h3>
          <div className="space-y-3">
            {data.expenses_by_category.map((cat) => (
              <div key={cat.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text">{cat.label}</span>
                  <span className="text-text-muted tabular-nums">{formatCurrency(cat.amount)}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-2 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(cat.amount / maxCatAmount) * 100}%`,
                      backgroundColor: CHART_COLORS.red,
                      opacity: 0.7 + (cat.amount / maxCatAmount) * 0.3,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monthly Report */}
      <div className="bg-surface border border-border rounded-[12px] p-5 mt-6">
        <h3 className="text-sm font-medium text-text mb-4">Monatsbericht generieren</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-text-muted mb-1">Monat</label>
            <select
              value={reportMonth}
              onChange={(e) => setReportMonth(Number(e.target.value))}
              className="input-field w-auto"
            >
              {MONTH_NAMES.map((name, i) => (
                <option key={i + 1} value={i + 1}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Jahr</label>
            <select
              value={reportYear}
              onChange={(e) => setReportYear(Number(e.target.value))}
              className="input-field w-auto"
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleMonthlyReport}
            disabled={generatingReport}
            className="btn-primary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {generatingReport ? 'Wird erstellt...' : 'PDF herunterladen'}
          </button>
        </div>
      </div>
    </div>
  )
}
