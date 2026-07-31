import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppNavigate } from '../../utils/transitions'
import DataTable, { type Column } from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import DeleteDialog from '../../components/DeleteDialog'
import PageHeader from '../../components/PageHeader'
import HostingerImportModal from './HostingerImportModal'
import Fab from '../../components/Fab'
import LoadingIndicator from '../../components/LoadingIndicator'
import {
  getExpenses, getExpenseSummary, deleteExpense, createExpense, setExpensePayment,
} from '../../api/expenses'
import { toastWithUndo } from '../../utils/undoToast'
import { canDelete } from '../../utils/permissions'
import { useAuthStore } from '../../store/authStore'
import { formatCurrency, formatDate } from '../../utils/formatters'
import { recurrenceLabel } from '../../utils/expenseRecurrence'
import toast from 'react-hot-toast'
import type { Expense, ExpenseSummary } from '../../types'
import Select from '../../components/Select'
import SegmentedButtons from '../../components/SegmentedButtons'
import Icon from '../../components/Icon'

type PaidFilter = 'all' | 'paid' | 'open'

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
  const navigate = useAppNavigate()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [paidFilter, setPaidFilter] = useState<PaidFilter>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showHostinger, setShowHostinger] = useState(false)
  const [summary, setSummary] = useState<ExpenseSummary | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  // Die ausgewählten ZEILEN, nicht nur ihre IDs: „alle auswählen" kann über die
  // Seitengrenze hinausgehen, und dann liegen die Objekte nicht mehr in
  // `expenses` — ohne sie könnte weder gelöscht noch wiederhergestellt werden.
  const [selected, setSelected] = useState<Map<string, Expense>>(new Map())
  const [bulkOpen, setBulkOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  // Löschen ist Sache des Bereichs-Inhabers; die verbindliche Sperre sitzt
  // serverseitig (middleware/permissions.py), das hier blendet nur aus.
  const mayDelete = canDelete(useAuthStore((st) => st.role))

  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getExpenses({
        page,
        search: search || undefined,
        category: categoryFilter || undefined,
        paid: paidFilter === 'all' ? undefined : paidFilter === 'paid',
        from: dateFrom || undefined,
        to: dateTo || undefined,
      })
      setExpenses(res.items)
      setTotal(res.total)
    } catch {
      // error handled globally
    }
    setLoading(false)
  }, [page, search, categoryFilter, paidFilter, dateFrom, dateTo])

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

  /** Alle Felder inkl. `external_ref` — eine wiederhergestellte importierte
   *  Ausgabe muss ihre Herkunft behalten, sonst bucht der nächste
   *  Hostinger-Lauf denselben Zeitraum ein zweites Mal. Die ID ist neu
   *  (Repo-Muster: Wiederherstellen = Neuanlage). */
  const restore = (e: Expense) => createExpense({
    description: e.description,
    category: e.category,
    amount: Number(e.amount),
    date: e.date,
    vendor: e.vendor || undefined,
    recurring: e.recurring,
    recurrence: e.recurrence ?? (e.recurring ? 'monthly' : null),
    notes: e.notes || undefined,
    paid: e.paid,
    paid_at: e.paid_at,
    external_ref: e.external_ref,
  })

  const refresh = () => { fetchData(); fetchSummary() }

  const togglePaid = async (e: Expense) => {
    const prev = { paid: e.paid, paid_at: e.paid_at }
    const nextPaid = !e.paid
    const next = {
      paid: nextPaid,
      paid_at: nextPaid ? (e.paid_at || e.date) : null,
    }
    setExpenses((list) =>
      list.map((row) => (row.id === e.id ? { ...row, ...next } : row)),
    )
    try {
      await setExpensePayment(e.id, next)
      refresh()
      toastWithUndo(
        nextPaid ? 'Als bezahlt markiert.' : 'Als offen markiert.',
        async () => {
          await setExpensePayment(e.id, prev)
          refresh()
        },
      )
    } catch {
      setExpenses((list) =>
        list.map((row) => (row.id === e.id ? { ...row, ...prev } : row)),
      )
      toast.error('Zahlungsstand konnte nicht geändert werden.')
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    const deleted = expenses.find((e) => e.id === deleteId)
    try {
      await deleteExpense(deleteId)
      setDeleteId(null)
      refresh()
      if (deleted) {
        toastWithUndo('Ausgabe gelöscht.', async () => {
          await restore(deleted)
          refresh()
        })
      } else {
        toast.success('Ausgabe gelöscht.')
      }
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  const handleBulkDelete = async () => {
    if (!selected.size || busy) return
    setBusy(true)
    // Die Zeilen liegen bereits im State (auch seitenübergreifend) — nach dem
    // Löschen gäbe es nichts mehr, woraus „Rückgängig" sie bauen könnte.
    const doomed = [...selected.values()]
    let failed = 0
    const gone: Expense[] = []
    for (const e of doomed) {
      try {
        await deleteExpense(e.id)
        gone.push(e)
      } catch {
        failed++
      }
    }
    setBulkOpen(false)
    setSelected(new Map())
    setBusy(false)
    refresh()
    if (!gone.length) {
      toast.error('Löschen fehlgeschlagen.')
      return
    }
    const label = `${gone.length} Ausgabe${gone.length === 1 ? '' : 'n'} gelöscht`
      + (failed ? `, ${failed} fehlgeschlagen` : '') + '.'
    toastWithUndo(label, async () => {
      for (const e of gone) {
        try {
          await restore(e)
        } catch { /* z. B. 409, falls dieselbe Herkunft zwischenzeitlich existiert */ }
      }
      refresh()
    })
  }

  const toggleSelect = (e: Expense) => setSelected((prev) => {
    const next = new Map(prev)
    if (next.has(e.id)) next.delete(e.id); else next.set(e.id, e)
    return next
  })

  const pageSelected = expenses.length > 0 && expenses.every((e) => selected.has(e.id))

  const toggleSelectAll = () => setSelected((prev) => {
    const next = new Map(prev)
    if (pageSelected) expenses.forEach((e) => next.delete(e.id))
    else expenses.forEach((e) => next.set(e.id, e))
    return next
  })

  /** Alle Zeilen des aktuellen Filters auswählen — auch die auf anderen Seiten.
   *  Ein Abruf (page_size ist serverseitig auf 1000 gedeckelt). */
  const selectAllMatching = async () => {
    setBusy(true)
    try {
      const res = await getExpenses({
        page: 1, page_size: 1000,
        search: search || undefined,
        category: categoryFilter || undefined,
        paid: paidFilter === 'all' ? undefined : paidFilter === 'paid',
        from: dateFrom || undefined,
        to: dateTo || undefined,
      })
      setSelected(new Map(res.items.map((e) => [e.id, e])))
      if (res.total > res.items.length) {
        toast(`${res.items.length} von ${res.total} ausgewählt (Höchstmenge je Abruf).`)
      }
    } catch {
      toast.error('Auswahl fehlgeschlagen.')
    } finally {
      setBusy(false)
    }
  }

  /** Summe der Auswahl — im Bestätigungsdialog, damit man sieht, was weggeht. */
  const selectedSum = useMemo(
    () => [...selected.values()].reduce((acc, e) => acc + Number(e.amount), 0),
    [selected])

  const columns: Column<Expense>[] = useMemo(
    () => [
      // Auswahl und Löschen nur zeigen, wenn die Rolle es darf — sonst klickt
      // man ins Leere und bekommt bloß den 403 des Servers.
      ...(mayDelete ? [{
        key: 'select',
        label: (
          <input
            type="checkbox"
            aria-label="Alle auf dieser Seite auswählen"
            checked={pageSelected}
            onChange={toggleSelectAll}
            onClick={(ev) => ev.stopPropagation()}
            className="cursor-pointer"
          />
        ),
        render: (e: Expense) => (
          <input
            type="checkbox"
            aria-label={`${e.description} auswählen`}
            checked={selected.has(e.id)}
            onChange={() => toggleSelect(e)}
            onClick={(ev) => ev.stopPropagation()}
            className="cursor-pointer"
          />
        ),
      } satisfies Column<Expense>] : []),
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
        key: 'paid',
        label: 'Status',
        render: (e) => (
          <button
            type="button"
            title={e.paid ? 'Als offen markieren' : 'Als bezahlt markieren'}
            aria-label={e.paid
              ? `${e.description}: bezahlt — klicken zum Zurücksetzen`
              : `${e.description}: offen — klicken zum Bezahlen`}
            onClick={(ev) => { ev.stopPropagation(); void togglePaid(e) }}
            className={`md-state text-xs rounded-full px-2.5 py-1 font-medium ${
              e.paid
                ? 'bg-success/15 text-success'
                : 'bg-warning/15 text-warning'
            }`}
          >
            {e.paid ? 'Bezahlt' : 'Offen'}
          </button>
        ),
      },
      {
        key: 'recurring',
        label: 'Turnus',
        render: (e) => {
          const label = recurrenceLabel(e.recurrence) || (e.recurring ? 'monatlich' : '')
          return label ? (
            <span className="text-accent">{label}</span>
          ) : (
            <span className="text-text-muted">—</span>
          )
        },
      },
      ...(mayDelete ? [{
        key: 'actions',
        label: '',
        render: (e: Expense) => (
          <button
            type="button"
            title="Ausgabe löschen"
            aria-label={`${e.description} löschen`}
            onClick={(ev) => { ev.stopPropagation(); setDeleteId(e.id) }}
            className="md-state w-11 h-11 sm:w-8 sm:h-8 grid place-items-center rounded-full
                       text-text-muted hover:text-danger"
          ><Icon name="trash" size={16} className="mr-1 -mt-0.5" />
          </button>
        ),
      } satisfies Column<Expense>] : []),
    ],
    [mayDelete, expenses, selected, pageSelected],
  )

  return (
    <div>
      <PageHeader
        title="Ausgaben"
        actions={
          <button onClick={() => setShowHostinger(true)} className="btn-secondary text-sm"
                  title="Laufende VPS- und Domain-Kosten aus dem Hostinger-Konto übernehmen">
            Hostinger-Kosten übernehmen
          </button>
        }
      />
      {showHostinger && (
        <HostingerImportModal
          onClose={() => setShowHostinger(false)}
          onImported={() => { fetchData(); fetchSummary() }}
        />
      )}

      {/* Summary Cards */}
      <div className="md-stagger grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-surface border border-border rounded-card p-4">
          <div className="text-xs text-text-muted mb-1">
            Bezahlt {currentYear}
          </div>
          <div className="text-xl font-semibold text-text tabular-nums">
            {formatCurrency(summary?.total || 0)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-card p-4">
          <div className="text-xs text-text-muted mb-1">
            Diesen Monat
          </div>
          <div className="text-xl font-semibold text-text tabular-nums">
            {formatCurrency(monthTotal)}
          </div>
        </div>
        <div className="bg-surface border border-border rounded-card p-4">
          <div className="text-xs text-text-muted mb-1">
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
        <Select
          value={categoryFilter}
          onChange={(e) => {
            setCategoryFilter(e.target.value)
            setPage(1)
          }}
          className="w-auto"
          options={categoryOptions}
        />
        <SegmentedButtons
          dense
          value={paidFilter}
          onChange={(v) => { setPaidFilter(v); setPage(1) }}
          options={[
            { value: 'all', label: 'Alle' },
            { value: 'paid', label: 'Bezahlt' },
            { value: 'open', label: 'Offen' },
          ]}
        />
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
        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-text-muted">{selected.size} ausgewählt</span>
            {selected.size < total && (
              <button onClick={selectAllMatching} disabled={busy}
                      className="md-state text-accent text-xs rounded-xs px-1">
                alle {total} auswählen
              </button>
            )}
            <button onClick={() => setBulkOpen(true)} disabled={busy}
                    className="btn-danger text-xs !py-1.5 !px-4">
              Löschen
            </button>
            <button onClick={() => setSelected(new Map())} aria-label="Auswahl aufheben"
                    className="md-state text-text-muted text-xs hover:text-text w-7 h-7 rounded-full">
              ×
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingIndicator />
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

      <Fab onClick={() => navigate('/ausgaben/neu')} label="Neue Ausgabe" />

      <DeleteDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Ausgabe löschen"
        message="Soll diese Ausgabe wirklich gelöscht werden?"
      />

      <DeleteDialog
        isOpen={bulkOpen}
        onClose={() => setBulkOpen(false)}
        onConfirm={handleBulkDelete}
        title={`${selected.size} Ausgabe${selected.size === 1 ? '' : 'n'} löschen`}
        message={`${selected.size} Ausgabe${selected.size === 1 ? '' : 'n'} über `
          + `${formatCurrency(selectedSum)} werden gelöscht. `
          + 'Direkt danach lässt sich das per „Rückgängig" zurücknehmen.'}
      />
    </div>
  )
}
