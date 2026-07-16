import { describe, it, expect } from 'vitest'
import { shouldReloadOnChunkError, CHUNK_RELOAD_COOLDOWN_MS } from './chunkReload'

describe('shouldReloadOnChunkError', () => {
  it('erster Fehler (kein vorheriger Reload) → true', () => {
    expect(shouldReloadOnChunkError(100_000, 0)).toBe(true)
  })
  it('innerhalb des Cooldowns → false (keine Reload-Schleife)', () => {
    const now = 100_000
    expect(shouldReloadOnChunkError(now, now - 5_000)).toBe(false)
    expect(shouldReloadOnChunkError(now, now)).toBe(false)
  })
  it('nach dem Cooldown → true', () => {
    const now = 100_000
    expect(shouldReloadOnChunkError(now, now - CHUNK_RELOAD_COOLDOWN_MS - 1)).toBe(true)
  })
  it('exakt am Cooldown-Rand → false (strikt größer)', () => {
    const now = 100_000
    expect(shouldReloadOnChunkError(now, now - CHUNK_RELOAD_COOLDOWN_MS)).toBe(false)
  })
  it('eigener Cooldown-Wert', () => {
    expect(shouldReloadOnChunkError(1_000, 500, 400)).toBe(true)
    expect(shouldReloadOnChunkError(1_000, 700, 400)).toBe(false)
  })
})
