import { describe, it, expect } from 'vitest'
import { buildBatchSummary, type GroupSel } from './batchSummary'
import type { DuplicateGroup, DuplicateMember } from '../../types'

const mem = (id: string, acts = 0): DuplicateMember => ({
  id, company: id, contact_name: null, role: null, email: null, website: null,
  phone: null, source: null, status: 'new', activity_count: acts, created_at: null,
})

const group = (reason: string, ids: string[], keeper: string): DuplicateGroup => ({
  score: 0.9, reason, suggested_keeper_id: keeper, members: ids.map((i) => mem(i)),
})

describe('buildBatchSummary', () => {
  it('zählt Merges, Löschungen und Aktivitäten der eingeschlossenen Gruppen', () => {
    const groups: DuplicateGroup[] = [
      { ...group('firm', ['a', 'b'], 'a'), members: [mem('a'), mem('b', 3)] },
      group('same_person', ['c', 'd'], 'c'),
    ]
    const sel: Record<number, GroupSel> = {
      0: { included: true, keeperId: 'a', dupIds: ['b'] },
      1: { included: true, keeperId: 'c', dupIds: ['d'] },
    }
    const s = buildBatchSummary(groups, sel)
    expect(s.groupCount).toBe(2)
    expect(s.deleteCount).toBe(2)
    expect(s.activityCount).toBe(3)   // b hat 3 Aktivitäten
    expect(s.colleagueCount).toBe(0)
  })

  it('ignoriert nicht eingeschlossene Gruppen', () => {
    const groups = [group('firm', ['a', 'b'], 'a')]
    const sel = { 0: { included: false, keeperId: 'a', dupIds: ['b'] } }
    expect(buildBatchSummary(groups, sel).groupCount).toBe(0)
  })

  it('zählt Kollegen/Fuzzy-Gruppen als Warnung', () => {
    const groups = [group('colleagues', ['a', 'b'], 'a'), group('fuzzy', ['c', 'd'], 'c')]
    const sel = {
      0: { included: true, keeperId: 'a', dupIds: ['b'] },
      1: { included: true, keeperId: 'c', dupIds: ['d'] },
    }
    expect(buildBatchSummary(groups, sel).colleagueCount).toBe(2)
  })

  it('erkennt Überschneidungen (Lead in mehreren Gruppen)', () => {
    const groups = [group('firm', ['a', 'x'], 'a'), group('firm', ['c', 'x'], 'c')]
    const sel = {
      0: { included: true, keeperId: 'a', dupIds: ['x'] },
      1: { included: true, keeperId: 'c', dupIds: ['x'] },
    }
    expect(buildBatchSummary(groups, sel).overlaps).toBe(true)
  })

  it('überspringt Gruppen ohne gewählte Duplikate', () => {
    const groups = [group('firm', ['a', 'b'], 'a')]
    const sel = { 0: { included: true, keeperId: 'a', dupIds: [] } }
    expect(buildBatchSummary(groups, sel).groupCount).toBe(0)
  })
})
