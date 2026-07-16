import { describe, it, expect } from 'vitest'
import {
  isItemActive,
  buildNavGroups,
  isGroupOpen,
  toggleCollapsed,
  type NavItem,
  type NavGroupMeta,
} from './navGroups'

const items: NavItem[] = [
  { to: '/', label: 'Dashboard' },
  { to: '/rainmaker', label: 'Rainmaker' },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/akquise', label: 'Akquise', adminOnly: true },
  { to: '/kunden', label: 'Kunden' },
  { to: '/benutzer', label: 'Benutzer', adminOnly: true },
  { to: '/einstellungen', label: 'Einstellungen' },
]

const meta: NavGroupMeta[] = [
  { title: 'Akquise', paths: ['/rainmaker', '/pipeline', '/akquise'] },
  { title: 'Kunden & Aufträge', paths: ['/kunden'] },
  { title: 'System', paths: ['/benutzer', '/einstellungen'] },
]

describe('isItemActive', () => {
  it('Dashboard nur bei exaktem /', () => {
    expect(isItemActive('/', '/')).toBe(true)
    expect(isItemActive('/kunden', '/')).toBe(false)
  })
  it('Präfix-Match für Unterseiten', () => {
    expect(isItemActive('/kunden', '/kunden')).toBe(true)
    expect(isItemActive('/kunden/123', '/kunden')).toBe(true)
    expect(isItemActive('/kundenxyz', '/kunden')).toBe(false) // kein falscher Präfix-Treffer
    expect(isItemActive('/pipeline/leads/1', '/pipeline')).toBe(true)
  })
})

describe('buildNavGroups', () => {
  it('Dashboard einzeln + Admin sieht alles', () => {
    const { dashboard, groups } = buildNavGroups(items, meta, true)
    expect(dashboard?.to).toBe('/')
    expect(groups.map((g) => g.title)).toEqual(['Akquise', 'Kunden & Aufträge', 'System'])
    expect(groups[0].items.map((i) => i.to)).toEqual(['/rainmaker', '/pipeline', '/akquise'])
  })
  it('Nicht-Admin: adminOnly-Items gefiltert', () => {
    const { groups } = buildNavGroups(items, meta, false)
    const akquise = groups.find((g) => g.title === 'Akquise')!
    expect(akquise.items.map((i) => i.to)).toEqual(['/rainmaker', '/pipeline']) // /akquise raus
    const system = groups.find((g) => g.title === 'System')!
    expect(system.items.map((i) => i.to)).toEqual(['/einstellungen']) // /benutzer raus
  })
  it('leere Gruppe (alle Items adminOnly, Nicht-Admin) fällt weg', () => {
    const m: NavGroupMeta[] = [{ title: 'NurAdmin', paths: ['/akquise', '/benutzer'] }]
    const { groups } = buildNavGroups(items, m, false)
    expect(groups).toEqual([])
  })
  it('unbekannte Pfade werden ignoriert', () => {
    const m: NavGroupMeta[] = [{ title: 'X', paths: ['/gibtsnicht', '/kunden'] }]
    const { groups } = buildNavGroups(items, m, true)
    expect(groups[0].items.map((i) => i.to)).toEqual(['/kunden'])
  })
})

describe('isGroupOpen', () => {
  const group = { title: 'Finanzen', items: [{ to: '/rechnungen', label: 'R' }, { to: '/ausgaben', label: 'A' }] }
  it('Rail eingeklappt → immer offen', () => {
    expect(isGroupOpen(group, { railCollapsed: true, collapsedTitles: ['Finanzen'], activePath: '/' })).toBe(true)
  })
  it('nicht manuell zugeklappt → offen', () => {
    expect(isGroupOpen(group, { railCollapsed: false, collapsedTitles: [], activePath: '/' })).toBe(true)
  })
  it('zugeklappt + keine aktive Route → zu', () => {
    expect(isGroupOpen(group, { railCollapsed: false, collapsedTitles: ['Finanzen'], activePath: '/kunden' })).toBe(false)
  })
  it('zugeklappt, aber enthält aktive Route → trotzdem offen', () => {
    expect(isGroupOpen(group, { railCollapsed: false, collapsedTitles: ['Finanzen'], activePath: '/rechnungen/7' })).toBe(true)
  })
})

describe('toggleCollapsed', () => {
  it('fügt hinzu / entfernt', () => {
    expect(toggleCollapsed([], 'A')).toEqual(['A'])
    expect(toggleCollapsed(['A', 'B'], 'A')).toEqual(['B'])
    expect(toggleCollapsed(['B'], 'A')).toEqual(['B', 'A'])
  })
})
