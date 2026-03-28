import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import { getExpenses, getExpenseSummary, deleteExpense } from '../../api/expenses'
import { formatCurrency, formatDate } from '../../utils/formatters'
import toast from 'react-hot-toast'
import type { Expense, ExpenseCategory, ExpenseSummary } from '../../types'

const categoryOptions: { value: string; label: string }[] = [
  { value: '', label: 'Alle Kategorien' },
  { value: 'hosting', label: 'Hosting' },
  { value: 'domain', label: 'Domain' },
  { value: 'software', label: 'Software' },
  { value: 'lizenz', label: 'Lizenz' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'ki_api', label: 'KI/API' },
  { value: 'werbung', label: 'Werbung' },
  { value: 'buero', label: 'Büro' },
  { value: 'reise', label: 'Reise' },
  { value: 'sonstige', label: 'Sonstige' },
]

export default function ExpenseList() {
  const navigate = useNavigate()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [summary, setSummary] = useState<ExpenseSummary | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getExpenses({
        page,
        search: search || undefined,
        category: categoryFilter || undefined,
        from: dateFrom || undefined,
        to: dateTo || undefined,
      })
      setExpenses(res.items)
      setTotal(res.total)
    } catch {
      // error handled globally
    }
    setLoading(false)
  }, [page, search, categoryFilter, dateFrom, dateTo])

  const fetchSummary = useCallback(async () => {
    try {
      const res = await getExpenseSummary(currentYear)
      setSummary(res)
    } catch {
      // silent
    }
  }, [currentYear])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  const monthTotal = useMemo(() => {
    if (!summary) return 0
    const monthEntry = summary.by_month.find((m) => m.month === currentMonth)
    return monthEntry?.total || 0
  }, [summary, currentMonth])

  const topCategory = useMemo(() => {
    if (!summary || summary.by_category.length === 0) return null
    const sorted = [...summary.by_category].sort((a, b) => b.total - a.total)
    return sorted[0]
  }, [summary])

  const topCategoryLabel = useMemo(() => {
    if (!topCategory) return '-'
    const opt = categoryOptions.find((o) => o.value === topCategory.category)
    return opt?.label || topCategory.category
  }, [topCategory])

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteExpense(deleteId)
      toast.success('Ausgabe gelöscht.')
      setDeleteId(null)
      fetchData()
      fetchSummary()
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  const columns: Column<Expense>[] = useMemo(
    () => [
      {
        key: 'date',
        label: 'Datum',
        render: (e) => formatDate(e.date),
      },
      { key: 'description', label: 'Beschreibung' },
      {
        key: 'category',
        label: 'Kategorie',
        render: (e) => <StatusBadge status={e.category} />,
      },
      {
        key: 'vendor',
        label: 'Anbieter',
        render: (e) => e.vendor || '-',
      },
      {
        key: 'amount',
        label: 'Betrag',
        render: (e) => (
          <span className="font-medium tabular-nums">{formatCurrency(e.amount)}</span>
        ),
      },
      {
        key: 'recurring',
        label: 'Wiederkehrend',
        render: (e) => (
          <span className={e.recurring ? 'text-accent' : 'text-text-muted'}>
            {e.recurring ? 'Ja' : 'Nein'}
          </span>
        ),
      },
    ],
    [],
  )

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Ausgaben</h2>
        <button onClick={() => navigate('/ausgaben/neu')} className="btn-primary">
          Neue Ausgabe
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Gesamt {currentYear}
          </div>
          <div className="text-xl font-semibold text-text tabular-nums">
            {formatCurrency(summary?.total || 0)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Diesen Monat
          </div>
          <div className="text-xl font-semibold text-text tabular-nums">
            {formatCurrency(monthTotal)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-[12px] p-4">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Top-Kategorie
          </div>
          <div className="text-xl font-semibold text-text">
            {topCategoryLabel}
            {topCategory && (
              <span className="text-sm text-text-muted ml-2 font-normal">
                {formatCurrency(topCategory.total)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center mb-4">
        <input
          type="text"
          placeholder="Ausgaben suchen..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="input-field max-w-xs"
        />
        <select
          value={categoryFilter}
          onChange={(e) => {
            setCategoryFilter(e.target.value)
            setPage(1)
          }}
          className="input-field w-auto"
        >
          {categoryOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value)
            setPage(1)
          }}
          className="input-field w-auto"
          placeholder="Von"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value)
            setPage(1)
          }}
          className="input-field w-auto"
          placeholder="Bis"
        />
      </div>

      {loading ? (
        <div className="text-text-muted py-12 text-center">Laden...</div>
      ) : (
        <DataTable
          columns={columns}
          data={expenses}
          onRowClick={(e) => navigate(`/ausgaben/${e.id}/bearbeiten`)}
          page={page}
          total={total}
          onPageChange={setPage}
        />
      )}

      <DeleteDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Ausgabe löschen"
        message="Soll diese Ausgabe wirklich gelöscht werden?"
      />
    </div>
  )
}
