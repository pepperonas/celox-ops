import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getInvoices } from '../api/invoices'
import { getContracts } from '../api/contracts'
import { getTimeEntries } from '../api/timeEntries'
import type { Invoice, Contract, TimeEntry } from '../types'

interface CalendarEvent {
  id: string
  type: 'invoice-due' | 'invoice-overdue' | 'contract-end' | 'time-entry'
  date: string
  label: string
  link: string
  color: string
}

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay()
  return day === 0 ? 6 : day - 1 // Monday = 0
}

function formatDate(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function toDateKey(dateStr: string): string {
  return dateStr.slice(0, 10)
}

export default function Calendar() {
  const navigate = useNavigate()
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const dateFrom = formatDate(year, month, 1)
      const lastDay = getDaysInMonth(year, month)
      const dateTo = formatDate(year, month, lastDay)

      const [invRes, conRes, teRes] = await Promise.all([
        getInvoices({ page_size: 1000 }),
        getContracts({ page_size: 1000 }),
        getTimeEntries({ date_from: dateFrom, date_to: dateTo, page_size: 1000 }),
      ])

      setInvoices(invRes.items)
      setContracts(conRes.items)
      setTimeEntries(teRes.items)
    } catch (err) {
      console.error('Calendar data fetch failed:', err)
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const events = useMemo(() => {
    const result: CalendarEvent[] = []
    const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate())

    for (const inv of invoices) {
      if (!inv.due_date) continue
      const dueKey = toDateKey(inv.due_date)
      if (inv.status === 'ueberfaellig' || (inv.status === 'gestellt' && dueKey < todayStr)) {
        result.push({
          id: `inv-overdue-${inv.id}`,
          type: 'invoice-overdue',
          date: dueKey,
          label: `RE ${inv.invoice_number} überfällig`,
          link: `/rechnungen/${inv.id}`,
          color: 'bg-red-500',
        })
      } else if (inv.status === 'gestellt') {
        result.push({
          id: `inv-due-${inv.id}`,
          type: 'invoice-due',
          date: dueKey,
          label: `RE ${inv.invoice_number} fällig`,
          link: `/rechnungen/${inv.id}`,
          color: 'bg-orange-500',
        })
      }
    }

    for (const con of contracts) {
      if (!con.end_date) continue
      const endKey = toDateKey(con.end_date)
      result.push({
        id: `con-${con.id}`,
        type: 'contract-end',
        date: endKey,
        label: `Vertrag: ${con.title}`,
        link: `/vertraege/${con.id}`,
        color: 'bg-purple-500',
      })
    }

    for (const te of timeEntries) {
      if (!te.date) continue
      const dateKey = toDateKey(te.date)
      result.push({
        id: `te-${te.id}`,
        type: 'time-entry',
        date: dateKey,
        label: `${te.hours}h ${te.customer_name || te.description}`,
        link: '/zeiterfassung',
        color: 'bg-green-500',
      })
    }

    return result
  }, [invoices, contracts, timeEntries, today])

  const eventsByDate = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {}
    for (const ev of events) {
      if (!map[ev.date]) map[ev.date] = []
      map[ev.date].push(ev)
    }
    return map
  }, [events])

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1) }
    else setMonth(m => m - 1)
    setSelectedDay(null)
  }

  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(y => y + 1) }
    else setMonth(m => m + 1)
    setSelectedDay(null)
  }

  const goToToday = () => {
    setYear(today.getFullYear())
    setMonth(today.getMonth())
    setSelectedDay(formatDate(today.getFullYear(), today.getMonth(), today.getDate()))
  }

  const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate())
  const daysInMonth = getDaysInMonth(year, month)
  const firstDay = getFirstDayOfWeek(year, month)
  const prevMonthDays = getDaysInMonth(year, month === 0 ? 11 : month - 1)

  // Build calendar grid cells
  const cells: { day: number; date: string; current: boolean }[] = []

  // Previous month trailing days
  for (let i = firstDay - 1; i >= 0; i--) {
    const d = prevMonthDays - i
    const m = month === 0 ? 11 : month - 1
    const y = month === 0 ? year - 1 : year
    cells.push({ day: d, date: formatDate(y, m, d), current: false })
  }

  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, date: formatDate(year, month, d), current: true })
  }

  // Next month leading days
  const remaining = 7 - (cells.length % 7)
  if (remaining < 7) {
    for (let d = 1; d <= remaining; d++) {
      const m = month === 11 ? 0 : month + 1
      const y = month === 11 ? year + 1 : year
      cells.push({ day: d, date: formatDate(y, m, d), current: false })
    }
  }

  const selectedEvents = selectedDay ? (eventsByDate[selectedDay] || []) : []

  // Mobile list view
  if (isMobile) {
    const daysWithEvents = Array.from({ length: daysInMonth }, (_, i) => {
      const date = formatDate(year, month, i + 1)
      return { day: i + 1, date, events: eventsByDate[date] || [] }
    }).filter(d => d.events.length > 0 || d.date === todayStr)

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text">Kalender</h1>
        </div>

        {/* Month nav */}
        <div className="flex items-center justify-between bg-surface rounded-lg p-4 border border-border">
          <button onClick={prevMonth} className="p-2 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-lg font-semibold text-text">{MONTH_NAMES[month]} {year}</span>
          <button onClick={nextMonth} className="p-2 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <button onClick={goToToday} className="btn-secondary text-sm">Heute</button>

        {loading ? (
          <div className="text-center py-12 text-text-muted">Laden...</div>
        ) : daysWithEvents.length === 0 ? (
          <div className="text-center py-12 text-text-muted">Keine Ereignisse in diesem Monat</div>
        ) : (
          <div className="space-y-3">
            {daysWithEvents.map(({ day, date, events: dayEvents }) => (
              <div key={date} className={`bg-surface rounded-lg border p-4 ${date === todayStr ? 'border-accent' : 'border-border'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {date === todayStr && <span className="w-2 h-2 rounded-full bg-accent" />}
                  <span className={`text-sm font-semibold ${date === todayStr ? 'text-accent' : 'text-text'}`}>
                    {day}. {MONTH_NAMES[month]}
                  </span>
                </div>
                {dayEvents.length > 0 ? (
                  <div className="space-y-1.5">
                    {dayEvents.map(ev => (
                      <button
                        key={ev.id}
                        onClick={() => navigate(ev.link)}
                        className="flex items-center gap-2 w-full text-left text-sm hover:bg-surface-2 rounded px-2 py-1 transition-colors"
                      >
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ev.color}`} />
                        <span className="text-text truncate">{ev.label}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <span className="text-xs text-text-muted">Heute</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Desktop grid view
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text">Kalender</h1>
      </div>

      {/* Header with month nav */}
      <div className="flex items-center justify-between bg-surface rounded-lg p-4 border border-border">
        <button onClick={prevMonth} className="p-2 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex items-center gap-4">
          <span className="text-lg font-semibold text-text">{MONTH_NAMES[month]} {year}</span>
          <button onClick={goToToday} className="btn-secondary text-xs py-1 px-3">Heute</button>
        </div>
        <button onClick={nextMonth} className="p-2 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-500" /> Rechnung fällig</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500" /> Überfällig</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-purple-500" /> Vertragsende</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500" /> Zeiterfassung</span>
      </div>

      {loading ? (
        <div className="text-center py-12 text-text-muted">Laden...</div>
      ) : (
        <>
          {/* Calendar grid */}
          <div className="bg-surface rounded-lg border border-border overflow-hidden">
            {/* Weekday header */}
            <div className="grid grid-cols-7 border-b border-border">
              {WEEKDAYS.map((day, i) => (
                <div
                  key={day}
                  className={`text-center text-xs font-semibold py-2.5 text-text-muted ${
                    i >= 5 ? 'bg-[#ffffff06]' : ''
                  }`}
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7">
              {cells.map((cell, idx) => {
                const dayEvents = eventsByDate[cell.date] || []
                const isToday = cell.date === todayStr
                const isSelected = cell.date === selectedDay
                const isWeekend = idx % 7 >= 5

                return (
                  <button
                    key={`${cell.date}-${idx}`}
                    onClick={() => setSelectedDay(isSelected ? null : cell.date)}
                    className={`
                      relative min-h-[5rem] p-1.5 text-left border-b border-r border-border
                      transition-colors hover:bg-surface-2 focus:outline-none
                      ${isWeekend ? 'bg-[#ffffff04]' : 'bg-surface'}
                      ${isSelected ? 'ring-1 ring-accent ring-inset' : ''}
                      ${!cell.current ? 'opacity-40' : ''}
                    `}
                  >
                    <span
                      className={`
                        inline-flex items-center justify-center w-6 h-6 text-xs font-medium rounded-full
                        ${isToday ? 'bg-accent text-white' : 'text-text'}
                      `}
                    >
                      {cell.day}
                    </span>

                    {/* Event dots */}
                    {dayEvents.length > 0 && (
                      <div className="mt-0.5 space-y-0.5">
                        {dayEvents.slice(0, 3).map(ev => (
                          <div key={ev.id} className="flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${ev.color}`} />
                            <span className="text-[10px] text-text-muted truncate leading-tight">{ev.label}</span>
                          </div>
                        ))}
                        {dayEvents.length > 3 && (
                          <span className="text-[10px] text-text-muted pl-2.5">+{dayEvents.length - 3} mehr</span>
                        )}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Selected day detail */}
          {selectedDay && (
            <div className="bg-surface rounded-lg border border-border p-5">
              <h3 className="text-sm font-semibold text-text mb-3">
                {parseInt(selectedDay.slice(8, 10))}. {MONTH_NAMES[parseInt(selectedDay.slice(5, 7)) - 1]} {selectedDay.slice(0, 4)}
              </h3>
              {selectedEvents.length === 0 ? (
                <p className="text-sm text-text-muted">Keine Ereignisse an diesem Tag</p>
              ) : (
                <div className="space-y-2">
                  {selectedEvents.map(ev => (
                    <button
                      key={ev.id}
                      onClick={() => navigate(ev.link)}
                      className="flex items-center gap-3 w-full text-left px-3 py-2 rounded-md hover:bg-surface-2 transition-colors"
                    >
                      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${ev.color}`} />
                      <span className="text-sm text-text">{ev.label}</span>
                      <svg className="w-4 h-4 text-text-muted ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
