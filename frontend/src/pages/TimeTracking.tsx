import { useEffect, useState, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import { getCustomers } from '../api/customers'
import {
  getTimeEntries,
  createTimeEntry,
  deleteTimeEntry,
  getTimeEntrySummary,
} from '../api/timeEntries'
import type {
  Customer,
  TimeEntry,
  TimeEntryCreate,
  TimeEntrySummary,
} from '../types'

const TIMER_STORAGE_KEY = 'celox_timer_state'

interface TimerState {
  running: boolean
  startTime: number
  customerId: string
  description: string
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export default function TimeTracking() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [entries, setEntries] = useState<TimeEntry[]>([])
  const [summary, setSummary] = useState<TimeEntrySummary[]>([])
  const [loading, setLoading] = useState(true)

  // Timer state
  const [timerRunning, setTimerRunning] = useState(false)
  const [timerSeconds, setTimerSeconds] = useState(0)
  const [timerCustomerId, setTimerCustomerId] = useState('')
  const [timerDescription, setTimerDescription] = useState('')
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)

  // Manual entry
  const [manualOpen, setManualOpen] = useState(false)
  const [manualCustomerId, setManualCustomerId] = useState('')
  const [manualDate, setManualDate] = useState(
    new Date().toISOString().split('T')[0],
  )
  const [manualHours, setManualHours] = useState('')
  const [manualDescription, setManualDescription] = useState('')
  const [manualRate, setManualRate] = useState('')
  const [manualNotes, setManualNotes] = useState('')

  // Filters
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterFrom, setFilterFrom] = useState('')
  const [filterTo, setFilterTo] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [custRes, entriesRes, summaryRes] = await Promise.all([
        getCustomers({ page_size: 200 }),
        getTimeEntries({
          customer_id: filterCustomer || undefined,
          date_from: filterFrom || undefined,
          date_to: filterTo || undefined,
          page_size: 100,
        }),
        getTimeEntrySummary(),
      ])
      setCustomers(custRes.items)
      setEntries(entriesRes.items)
      setSummary(summaryRes)
    } catch {
      toast.error('Fehler beim Laden der Daten')
    } finally {
      setLoading(false)
    }
  }, [filterCustomer, filterFrom, filterTo])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Restore timer from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(TIMER_STORAGE_KEY)
    if (saved) {
      try {
        const state: TimerState = JSON.parse(saved)
        if (state.running) {
          const elapsed = Math.floor((Date.now() - state.startTime) / 1000)
          setTimerRunning(true)
          setTimerSeconds(elapsed)
          setTimerCustomerId(state.customerId)
          setTimerDescription(state.description)
          startTimeRef.current = state.startTime
        }
      } catch {
        localStorage.removeItem(TIMER_STORAGE_KEY)
      }
    }
  }, [])

  // Timer interval
  useEffect(() => {
    if (timerRunning) {
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor(
          (Date.now() - startTimeRef.current) / 1000,
        )
        setTimerSeconds(elapsed)
      }, 1000)
    } else if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [timerRunning])

  const startTimer = () => {
    if (!timerCustomerId) {
      toast.error('Bitte Kunde auswählen')
      return
    }
    if (!timerDescription.trim()) {
      toast.error('Bitte Beschreibung eingeben')
      return
    }
    const now = Date.now()
    startTimeRef.current = now
    setTimerRunning(true)
    setTimerSeconds(0)
    localStorage.setItem(
      TIMER_STORAGE_KEY,
      JSON.stringify({
        running: true,
        startTime: now,
        customerId: timerCustomerId,
        description: timerDescription,
      } as TimerState),
    )
  }

  const stopTimer = async () => {
    setTimerRunning(false)
    localStorage.removeItem(TIMER_STORAGE_KEY)

    const elapsed = Math.floor(
      (Date.now() - startTimeRef.current) / 1000,
    )
    const hours = Math.round((elapsed / 3600) * 100) / 100

    if (hours < 0.01) {
      toast.error('Zu kurz — weniger als 1 Minute')
      return
    }

    try {
      const data: TimeEntryCreate = {
        customer_id: timerCustomerId,
        description: timerDescription,
        date: new Date().toISOString().split('T')[0],
        hours,
      }
      await createTimeEntry(data)
      toast.success(`${hours}h erfasst`)
      setTimerDescription('')
      setTimerSeconds(0)
      loadData()
    } catch {
      toast.error('Fehler beim Speichern')
    }
  }

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!manualCustomerId || !manualHours || !manualDescription.trim()) {
      toast.error('Bitte alle Pflichtfelder ausfüllen')
      return
    }
    try {
      const data: TimeEntryCreate = {
        customer_id: manualCustomerId,
        description: manualDescription,
        date: manualDate,
        hours: parseFloat(manualHours),
        ...(manualRate ? { hourly_rate: parseFloat(manualRate) } : {}),
        ...(manualNotes ? { notes: manualNotes } : {}),
      }
      await createTimeEntry(data)
      toast.success('Eintrag gespeichert')
      setManualDescription('')
      setManualHours('')
      setManualRate('')
      setManualNotes('')
      loadData()
    } catch {
      toast.error('Fehler beim Speichern')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Eintrag wirklich löschen?')) return
    try {
      await deleteTimeEntry(id)
      toast.success('Gelöscht')
      loadData()
    } catch {
      toast.error('Fehler beim Löschen')
    }
  }

  const totalUninvoicedHours = summary.reduce(
    (acc, s) => acc + s.uninvoiced_hours,
    0,
  )
  const totalUninvoicedAmount = summary.reduce((acc, s) => {
    return acc + s.total_amount
  }, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold text-text">Zeiterfassung</h1>

      {/* Timer Section */}
      <div className="card p-6">
        <h2 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-4">
          Timer
        </h2>
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-end">
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-text-muted mb-1">Kunde</label>
            <select
              value={timerCustomerId}
              onChange={(e) => setTimerCustomerId(e.target.value)}
              disabled={timerRunning}
              className="input w-full"
            >
              <option value="">-- Kunde wählen --</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.company ? ` (${c.company})` : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-text-muted mb-1">
              Beschreibung
            </label>
            <input
              type="text"
              value={timerDescription}
              onChange={(e) => setTimerDescription(e.target.value)}
              disabled={timerRunning}
              placeholder="Was wird gemacht?"
              className="input w-full"
            />
          </div>
          <div className="flex items-center gap-4">
            <div
              className={`font-mono text-3xl tabular-nums tracking-tight ${
                timerRunning ? 'text-green-400' : 'text-text-muted'
              }`}
            >
              {formatDuration(timerSeconds)}
            </div>
            {!timerRunning ? (
              <button onClick={startTimer} className="btn-primary px-6 py-2.5">
                <svg
                  className="w-5 h-5 mr-1 inline"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
                Start
              </button>
            ) : (
              <button
                onClick={stopTimer}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2.5 rounded-[6px] font-medium text-sm transition-colors"
              >
                <svg
                  className="w-5 h-5 mr-1 inline"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
                Stopp
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Manual Entry */}
      <div className="card">
        <button
          onClick={() => setManualOpen(!manualOpen)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-surface-2 transition-colors"
        >
          <span className="text-sm font-medium text-text">
            + Manueller Eintrag
          </span>
          <svg
            className={`w-4 h-4 text-text-muted transition-transform ${manualOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        {manualOpen && (
          <form
            onSubmit={handleManualSubmit}
            className="px-6 pb-6 grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            <div>
              <label className="block text-xs text-text-muted mb-1">
                Kunde *
              </label>
              <select
                value={manualCustomerId}
                onChange={(e) => setManualCustomerId(e.target.value)}
                className="input w-full"
                required
              >
                <option value="">-- Kunde wählen --</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                    {c.company ? ` (${c.company})` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">
                Datum *
              </label>
              <input
                type="date"
                value={manualDate}
                onChange={(e) => setManualDate(e.target.value)}
                className="input w-full"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">
                Stunden *
              </label>
              <input
                type="number"
                step="0.25"
                min="0.01"
                value={manualHours}
                onChange={(e) => setManualHours(e.target.value)}
                placeholder="z.B. 2.5"
                className="input w-full"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs text-text-muted mb-1">
                Beschreibung *
              </label>
              <input
                type="text"
                value={manualDescription}
                onChange={(e) => setManualDescription(e.target.value)}
                placeholder="Tätigkeit beschreiben"
                className="input w-full"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">
                Stundensatz (optional)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={manualRate}
                onChange={(e) => setManualRate(e.target.value)}
                placeholder="z.B. 95.00"
                className="input w-full"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs text-text-muted mb-1">
                Notizen (optional)
              </label>
              <input
                type="text"
                value={manualNotes}
                onChange={(e) => setManualNotes(e.target.value)}
                placeholder="Zusätzliche Hinweise"
                className="input w-full"
              />
            </div>
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full">
                Speichern
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-text-muted mb-1">Kunde</label>
            <select
              value={filterCustomer}
              onChange={(e) => setFilterCustomer(e.target.value)}
              className="input"
            >
              <option value="">Alle</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Von</label>
            <input
              type="date"
              value={filterFrom}
              onChange={(e) => setFilterFrom(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Bis</label>
            <input
              type="date"
              value={filterTo}
              onChange={(e) => setFilterTo(e.target.value)}
              className="input"
            />
          </div>
          {(filterCustomer || filterFrom || filterTo) && (
            <button
              onClick={() => {
                setFilterCustomer('')
                setFilterFrom('')
                setFilterTo('')
              }}
              className="btn-secondary text-xs"
            >
              Filter zurücksetzen
            </button>
          )}
        </div>
      </div>

      {/* Entries Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-muted">
                <th className="px-4 py-3 font-medium">Datum</th>
                <th className="px-4 py-3 font-medium">Kunde</th>
                <th className="px-4 py-3 font-medium">Beschreibung</th>
                <th className="px-4 py-3 font-medium text-right">Stunden</th>
                <th className="px-4 py-3 font-medium text-right">Betrag</th>
                <th className="px-4 py-3 font-medium text-center">Status</th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-text-muted"
                  >
                    Keine Einträge vorhanden
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-border hover:bg-surface-2 transition-colors"
                  >
                    <td className="px-4 py-3 text-text whitespace-nowrap">
                      {formatDate(entry.date)}
                    </td>
                    <td className="px-4 py-3 text-text">
                      {entry.customer_name}
                    </td>
                    <td className="px-4 py-3 text-text-muted max-w-xs truncate">
                      {entry.description}
                    </td>
                    <td className="px-4 py-3 text-text text-right tabular-nums">
                      {Number(entry.hours).toFixed(2)}h
                    </td>
                    <td className="px-4 py-3 text-text text-right tabular-nums">
                      {entry.hourly_rate
                        ? `${(Number(entry.hours) * Number(entry.hourly_rate)).toFixed(2)} €`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {entry.invoiced ? (
                        <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-green-500/15 text-green-400">
                          Abgerechnet
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-[#d2992233] text-warning">
                          Offen
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="text-text-muted hover:text-danger transition-colors"
                        title="Löschen"
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Summary */}
        {summary.length > 0 && (
          <div className="px-4 py-3 border-t border-border bg-surface-2/50 flex items-center justify-between">
            <span className="text-sm text-text-muted">
              {totalUninvoicedHours.toFixed(1)} Stunden offen
              {totalUninvoicedAmount > 0 &&
                ` (${totalUninvoicedAmount.toFixed(2)} €)`}
            </span>
            <div className="flex gap-4 text-xs text-text-muted">
              {summary.map((s) => (
                <span key={s.customer_id}>
                  {s.customer_name}: {Number(s.total_hours).toFixed(1)}h
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
