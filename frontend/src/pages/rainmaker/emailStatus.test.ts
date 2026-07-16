import { describe, it, expect } from 'vitest'
import { emailStatusInfo, EMAIL_STATUS, EMAIL_DELIVERABLE, EMAIL_PROBLEM } from './emailStatus'

describe('emailStatusInfo', () => {
  it('bekannter Status → Info-Objekt', () => {
    expect(emailStatusInfo('valid')?.label).toBe('✓ E-Mail ok')
    expect(emailStatusInfo('no_mx')?.cls).toBe('text-danger')
  })
  it('null/undefined/leer → null', () => {
    expect(emailStatusInfo(null)).toBeNull()
    expect(emailStatusInfo(undefined)).toBeNull()
    expect(emailStatusInfo('')).toBeNull()
  })
  it('unbekannter Status → null (kein Crash)', () => {
    expect(emailStatusInfo('gibtsnicht')).toBeNull()
  })
})

describe('EMAIL_DELIVERABLE / EMAIL_PROBLEM', () => {
  it('disjunkt', () => {
    for (const s of EMAIL_DELIVERABLE) expect(EMAIL_PROBLEM.has(s)).toBe(false)
  })
  it('zustellbar = valid/role, Problem = disposable/no_mx/invalid_syntax', () => {
    expect([...EMAIL_DELIVERABLE].sort()).toEqual(['role', 'valid'])
    expect([...EMAIL_PROBLEM].sort()).toEqual(['disposable', 'invalid_syntax', 'no_mx'])
  })
  it('jeder Deliverable/Problem-Key hat einen EMAIL_STATUS-Eintrag', () => {
    for (const s of [...EMAIL_DELIVERABLE, ...EMAIL_PROBLEM]) {
      expect(EMAIL_STATUS[s]).toBeTruthy()
    }
  })
})
