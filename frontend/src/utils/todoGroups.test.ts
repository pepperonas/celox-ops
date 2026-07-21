import { describe, expect, it } from 'vitest'
import { dueLabel, groupOf, groupTodos, daysUntil } from './todoGroups'
import type { Todo } from '../types'

const TODAY = new Date(2026, 6, 21) // 21.07.2026, lokal

function todo(over: Partial<Todo> = {}): Todo {
  return {
    id: Math.random().toString(36).slice(2),
    title: 'Test', notes: null, customer_id: null, lead_id: null,
    due_date: null, priority: 'normal', status: 'offen', done_at: null,
    sort_order: 0, created_at: '2026-07-01T10:00:00Z', updated_at: '2026-07-01T10:00:00Z',
    customer_name: null, lead_name: null,
    ...over,
  }
}

describe('daysUntil', () => {
  it('rechnet in Kalendertagen, nicht in 24h-Blöcken', () => {
    expect(daysUntil('2026-07-21', TODAY)).toBe(0)
    expect(daysUntil('2026-07-22', TODAY)).toBe(1)
    expect(daysUntil('2026-07-20', TODAY)).toBe(-1)
  })

  it('über Monats- und Jahresgrenzen', () => {
    expect(daysUntil('2026-08-01', TODAY)).toBe(11)
    expect(daysUntil('2027-01-01', TODAY)).toBe(164)
  })

  it('NaN bei kaputtem Datum', () => {
    expect(daysUntil('', TODAY)).toBeNaN()
    expect(daysUntil('kaputt', TODAY)).toBeNaN()
  })
})

describe('groupOf', () => {
  it('erledigte immer in done — auch wenn überfällig', () => {
    expect(groupOf(todo({ status: 'erledigt', due_date: '2026-01-01' }), TODAY)).toBe('done')
  })

  it('offene nach Fälligkeit', () => {
    expect(groupOf(todo({ due_date: '2026-07-20' }), TODAY)).toBe('overdue')
    expect(groupOf(todo({ due_date: '2026-07-21' }), TODAY)).toBe('today')
    expect(groupOf(todo({ due_date: '2026-07-28' }), TODAY)).toBe('soon')
    expect(groupOf(todo({ due_date: '2026-07-29' }), TODAY)).toBe('later')
  })

  it('ohne Datum und bei kaputtem Datum in someday', () => {
    expect(groupOf(todo({ due_date: null }), TODAY)).toBe('someday')
    expect(groupOf(todo({ due_date: 'kaputt' }), TODAY)).toBe('someday')
  })
})

describe('groupTodos', () => {
  it('liefert nur befüllte Gruppen in fester Reihenfolge', () => {
    const groups = groupTodos([
      todo({ due_date: '2026-07-29' }),
      todo({ due_date: '2026-07-20' }),
      todo({ status: 'erledigt' }),
    ], TODAY)
    expect(groups.map((g) => g.key)).toEqual(['overdue', 'later', 'done'])
  })

  it('leere Liste ergibt keine Gruppen', () => {
    expect(groupTodos([], TODAY)).toEqual([])
  })

  it('sortiert innerhalb der Gruppe nach Fälligkeit, dann Priorität', () => {
    const groups = groupTodos([
      todo({ title: 'C', due_date: '2026-07-25', priority: 'niedrig' }),
      todo({ title: 'A', due_date: '2026-07-23' }),
      todo({ title: 'B', due_date: '2026-07-25', priority: 'hoch' }),
    ], TODAY)
    expect(groups[0].items.map((t) => t.title)).toEqual(['A', 'B', 'C'])
  })

  it('erledigte: zuletzt abgehakte zuerst', () => {
    const groups = groupTodos([
      todo({ title: 'alt', status: 'erledigt', done_at: '2026-07-01T08:00:00Z' }),
      todo({ title: 'neu', status: 'erledigt', done_at: '2026-07-20T08:00:00Z' }),
    ], TODAY)
    expect(groups[0].items.map((t) => t.title)).toEqual(['neu', 'alt'])
  })

  it('ohne Datum sortiert hinter datierten (innerhalb someday egal)', () => {
    const groups = groupTodos([todo({ priority: 'niedrig' }), todo({ priority: 'hoch' })], TODAY)
    expect(groups[0].key).toBe('someday')
    expect(groups[0].items[0].priority).toBe('hoch')
  })

  it('mutiert die Eingabeliste nicht in ihrer Länge', () => {
    const input = [todo(), todo({ due_date: '2026-07-20' })]
    const total = groupTodos(input, TODAY).reduce((n, g) => n + g.items.length, 0)
    expect(total).toBe(2)
    expect(input).toHaveLength(2)
  })
})

describe('dueLabel', () => {
  it('sprechende Nahbereich-Labels', () => {
    expect(dueLabel('2026-07-21', TODAY)).toBe('heute')
    expect(dueLabel('2026-07-22', TODAY)).toBe('morgen')
    expect(dueLabel('2026-07-20', TODAY)).toBe('gestern')
    expect(dueLabel('2026-07-24', TODAY)).toBe('in 3 Tagen')
  })

  it('überfällig mit Tageszahl', () => {
    expect(dueLabel('2026-07-16', TODAY)).toBe('5 Tage überfällig')
  })

  it('fernes Datum als deutsches Datum', () => {
    expect(dueLabel('2026-09-01', TODAY)).toBe('01.09.2026')
  })

  it('leer ohne Datum', () => {
    expect(dueLabel(null, TODAY)).toBe('')
    expect(dueLabel('kaputt', TODAY)).toBe('')
  })
})
