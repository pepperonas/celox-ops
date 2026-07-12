import { describe, it, expect } from 'vitest'
import {
  STATUS_LABELS, STATUS_COLORS, PIPELINE_STATUSES,
  PRIORITY_LABELS, PRIORITY_TONE,
  ACTIVITY_TYPE_LABELS, ACTIVITY_TYPE_ICONS, OUTCOME_LABELS,
} from './constants'

describe('Rainmaker constants', () => {
  it('every pipeline status has a label and a colour', () => {
    for (const s of PIPELINE_STATUSES) {
      expect(STATUS_LABELS[s], `label for ${s}`).toBeTruthy()
      expect(STATUS_COLORS[s], `colour for ${s}`).toMatch(/^#[0-9a-fA-F]{6}$/)
    }
  })

  it('covers all eight lead statuses', () => {
    expect(Object.keys(STATUS_LABELS)).toHaveLength(8)
    expect(PIPELINE_STATUSES).toHaveLength(8)
  })

  it('priority labels and tones share the same keys', () => {
    expect(Object.keys(PRIORITY_TONE).sort()).toEqual(Object.keys(PRIORITY_LABELS).sort())
    expect(Object.keys(PRIORITY_LABELS)).toHaveLength(3)
  })

  it('every activity type has a label and an icon path', () => {
    for (const t of Object.keys(ACTIVITY_TYPE_LABELS)) {
      expect(ACTIVITY_TYPE_ICONS[t as keyof typeof ACTIVITY_TYPE_ICONS], `icon for ${t}`).toBeTruthy()
    }
    expect(Object.keys(ACTIVITY_TYPE_LABELS)).toHaveLength(6)
  })

  it('has labels for all outcomes', () => {
    expect(Object.keys(OUTCOME_LABELS)).toHaveLength(7)
  })
})
