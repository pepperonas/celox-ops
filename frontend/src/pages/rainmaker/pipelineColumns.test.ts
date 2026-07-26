import { describe, expect, it } from 'vitest'
import type { RainmakerLead, RainmakerLeadStatus } from '../../types'
import { PAGE_SIZE, countLabel, groupByStatus, nextCount, visibleCount } from './pipelineColumns'

const STATUSES: readonly RainmakerLeadStatus[] = ['new', 'contacted', 'won'] as const
const lead = (status: RainmakerLeadStatus, id = Math.random().toString(36).slice(2)) =>
  ({ id, status } as RainmakerLead)

describe('groupByStatus', () => {
  it('gruppiert in einem Durchlauf und erhält die Reihenfolge', () => {
    const a = lead('new', 'a'), b = lead('contacted', 'b'), c = lead('new', 'c')
    const out = groupByStatus([a, b, c], STATUSES)
    expect(out.new.map((l) => l.id)).toEqual(['a', 'c'])
    expect(out.contacted.map((l) => l.id)).toEqual(['b'])
  })

  it('legt jeden bekannten Status an — auch leer', () => {
    const out = groupByStatus([], STATUSES)
    expect(Object.keys(out).sort()).toEqual(['contacted', 'new', 'won'])
    expect(out.won).toEqual([])
  })

  it('ignoriert unbekannte Status ohne zu werfen', () => {
    const out = groupByStatus([lead('lost' as RainmakerLeadStatus)], STATUSES)
    expect(out.new).toEqual([])
  })
})

describe('visibleCount', () => {
  it('nutzt PAGE_SIZE als Default und cappt auf die Gesamtzahl', () => {
    expect(visibleCount(undefined, 351)).toBe(PAGE_SIZE)
    expect(visibleCount(undefined, 5)).toBe(5)
    expect(visibleCount(100, 40)).toBe(40)
  })
})

describe('nextCount', () => {
  it('erhöht um PAGE_SIZE, aber nie über die Gesamtzahl', () => {
    expect(nextCount(20, 351)).toBe(40)
    expect(nextCount(340, 351)).toBe(351)
    expect(nextCount(351, 351)).toBe(351)
  })
})

describe('countLabel', () => {
  it('zeigt „x von y" nur bei gekürzter Liste', () => {
    expect(countLabel(20, 351)).toBe('20 von 351')
    expect(countLabel(351, 351)).toBeNull()
    expect(countLabel(0, 0)).toBeNull()
  })
})
