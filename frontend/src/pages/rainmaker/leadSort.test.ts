import { describe, expect, it } from 'vitest'
import { regionKey, sortColumn, type LeadSort } from './leadSort'
import type { RainmakerLead } from '../../types'

function lead(over: Partial<RainmakerLead> = {}): RainmakerLead {
  return {
    id: Math.random().toString(36).slice(2),
    company: 'X', contact_name: null, role: null,
    employee_count: null, decision_maker: null,
    phone: null, email: null, address: null, website: null, source: null,
    status: 'new', priority: 'medium', value_estimate: null,
    tags: null, target: null, pinned: false, notes: null,
    created_at: '2026-07-01T00:00:00Z', updated_at: '2026-07-01T00:00:00Z',
    email_status: null, customer_id: null,
    next_action_type: null, next_action_due: null, next_action_id: null, needs_next_action: false,
    ...over,
  }
}

const order = (ls: RainmakerLead[], mode: LeadSort) => sortColumn(ls, mode).map((l) => l.company)

describe('regionKey', () => {
  it('zieht die 5-stellige PLZ aus der Adresse', () => {
    expect(regionKey('Großgartacher Straße 61, 74080 Heilbronn')).toBe('74080')
    expect(regionKey('Leipziger Platz 1, 10117 Berlin')).toBe('10117')
  })
  it('null ohne Adresse/PLZ', () => {
    expect(regionKey(null)).toBeNull()
    expect(regionKey('Musterweg 3, Berlin')).toBeNull()
  })
  it('greift nicht auf 4- oder 6-stellige Zahlen', () => {
    expect(regionKey('Haus 1234')).toBeNull()
    expect(regionKey('Nr. 123456')).toBeNull()
  })
})

describe('sortColumn — Mitarbeiter', () => {
  const ls = [
    lead({ company: 'klein', employee_count: 20 }),
    lead({ company: 'gross', employee_count: 5000 }),
    lead({ company: 'leer', employee_count: null }),
    lead({ company: 'mittel', employee_count: 300 }),
  ]
  it('viele zuerst, leer ans Ende', () => {
    expect(order(ls, 'employees_desc')).toEqual(['gross', 'mittel', 'klein', 'leer'])
  })
  it('wenige zuerst, leer trotzdem ans Ende', () => {
    expect(order(ls, 'employees_asc')).toEqual(['klein', 'mittel', 'gross', 'leer'])
  })
})

describe('sortColumn — Region', () => {
  it('nach PLZ aufsteigend, ohne PLZ ans Ende', () => {
    const ls = [
      lead({ company: 'muenchen', address: 'A, 80331 München' }),
      lead({ company: 'berlin', address: 'B, 10117 Berlin' }),
      lead({ company: 'ohne', address: null }),
      lead({ company: 'hamburg', address: 'C, 20095 Hamburg' }),
    ]
    expect(order(ls, 'region')).toEqual(['berlin', 'hamburg', 'muenchen', 'ohne'])
  })
})

describe('sortColumn — pinned & Stabilität', () => {
  it('gepinnte immer oben, egal welcher Modus', () => {
    const ls = [
      lead({ company: 'a', employee_count: 10 }),
      lead({ company: 'pin', employee_count: 5, pinned: true }),
      lead({ company: 'b', employee_count: 9000 }),
    ]
    expect(order(ls, 'employees_desc')[0]).toBe('pin')
    expect(order(ls, 'region')[0]).toBe('pin')
  })
  it('default hält die Eingangsreihenfolge (nur pinned-first)', () => {
    const ls = [lead({ company: 'a' }), lead({ company: 'b', pinned: true }), lead({ company: 'c' })]
    expect(order(ls, 'default')).toEqual(['b', 'a', 'c'])
  })
  it('mutiert die Eingabeliste nicht', () => {
    const ls = [lead({ company: 'a', employee_count: 1 }), lead({ company: 'b', employee_count: 2 })]
    sortColumn(ls, 'employees_desc')
    expect(ls.map((l) => l.company)).toEqual(['a', 'b'])
  })
})
