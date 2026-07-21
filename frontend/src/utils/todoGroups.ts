// Reine Gruppierungs-/Sortierlogik für die To-do-Liste — ohne DOM, damit sie
// unabhängig von der Komponente testbar bleibt.

import type { Todo } from '../types'

export type TodoGroupKey = 'overdue' | 'today' | 'soon' | 'later' | 'someday' | 'done'

export const TODO_GROUP_LABELS: Record<TodoGroupKey, string> = {
  overdue: 'Überfällig',
  today: 'Heute',
  soon: 'Diese Woche',
  later: 'Später',
  someday: 'Ohne Datum',
  done: 'Erledigt',
}

/** Reihenfolge der Gruppen in der Anzeige. */
export const TODO_GROUP_ORDER: TodoGroupKey[] = [
  'overdue', 'today', 'soon', 'later', 'someday', 'done',
]

/** Kalendertage zwischen zwei Daten (lokale Zeitzone, Uhrzeit ignoriert). */
export function daysUntil(dueISO: string, today: Date): number {
  const [y, m, d] = dueISO.split('-').map(Number)
  if (!y || !m || !d) return NaN
  const due = new Date(y, m - 1, d)
  const ref = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((due.getTime() - ref.getTime()) / 86_400_000)
}

export function groupOf(todo: Todo, today: Date): TodoGroupKey {
  if (todo.status === 'erledigt') return 'done'
  if (!todo.due_date) return 'someday'
  const diff = daysUntil(todo.due_date, today)
  if (isNaN(diff)) return 'someday'
  if (diff < 0) return 'overdue'
  if (diff === 0) return 'today'
  if (diff <= 7) return 'soon'
  return 'later'
}

const PRIORITY_RANK: Record<string, number> = { hoch: 0, normal: 1, niedrig: 2 }

/**
 * Gruppiert und sortiert: innerhalb einer Gruppe zuerst nach Fälligkeit
 * (früher zuerst), dann Priorität, dann manuelle Reihenfolge. Erledigte
 * zuletzt abgehakt zuerst — man will sehen, was man gerade geschafft hat.
 */
export function groupTodos(todos: Todo[], today: Date = new Date()): Array<{
  key: TodoGroupKey
  label: string
  items: Todo[]
}> {
  const buckets = new Map<TodoGroupKey, Todo[]>()
  for (const todo of todos) {
    const key = groupOf(todo, today)
    const list = buckets.get(key)
    if (list) list.push(todo)
    else buckets.set(key, [todo])
  }

  for (const [key, items] of buckets) {
    items.sort((a, b) => {
      if (key === 'done') {
        return (b.done_at || b.updated_at || '').localeCompare(a.done_at || a.updated_at || '')
      }
      if (a.due_date !== b.due_date) {
        if (!a.due_date) return 1
        if (!b.due_date) return -1
        return a.due_date.localeCompare(b.due_date)
      }
      const prio = (PRIORITY_RANK[a.priority] ?? 1) - (PRIORITY_RANK[b.priority] ?? 1)
      if (prio !== 0) return prio
      return (a.sort_order ?? 0) - (b.sort_order ?? 0)
    })
  }

  return TODO_GROUP_ORDER.filter((key) => buckets.get(key)?.length).map((key) => ({
    key,
    label: TODO_GROUP_LABELS[key],
    items: buckets.get(key)!,
  }))
}

/** Kurzes, sprechendes Fälligkeitslabel für die Karte. */
export function dueLabel(dueISO: string | null, today: Date = new Date()): string {
  if (!dueISO) return ''
  const diff = daysUntil(dueISO, today)
  if (isNaN(diff)) return ''
  if (diff === 0) return 'heute'
  if (diff === 1) return 'morgen'
  if (diff === -1) return 'gestern'
  if (diff < 0) return `${Math.abs(diff)} Tage überfällig`
  if (diff <= 7) return `in ${diff} Tagen`
  const [y, m, d] = dueISO.split('-')
  return `${d}.${m}.${y}`
}
