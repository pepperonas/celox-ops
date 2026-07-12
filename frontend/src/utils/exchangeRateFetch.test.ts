import { describe, it, expect, vi, beforeEach } from 'vitest'

// API-Client mocken — getUsdEurRate cached auf Modulebene, daher wird das
// Modul pro Test frisch importiert (vi.resetModules).
vi.mock('../api/client', () => ({ api: { get: vi.fn() } }))

async function freshModule() {
  vi.resetModules()
  const { api } = await import('../api/client')
  const mod = await import('./exchangeRate')
  return { api: api as unknown as { get: ReturnType<typeof vi.fn> }, mod }
}

describe('getUsdEurRate (Modul-Cache + Fallback)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('liefert den Backend-Kurs und cached ihn (nur EIN Request)', async () => {
    const { api, mod } = await freshModule()
    api.get.mockResolvedValue({ data: { rate: 0.87689, source: 'ecb' } })
    expect(await mod.getUsdEurRate()).toBe(0.87689)
    expect(await mod.getUsdEurRate()).toBe(0.87689)
    expect(api.get).toHaveBeenCalledTimes(1)
    expect(api.get).toHaveBeenCalledWith('/token-tracker/exchange-rate')
  })

  it('fällt bei API-Fehler auf 0.92 zurück und erlaubt späteren Retry', async () => {
    const { api, mod } = await freshModule()
    api.get.mockRejectedValueOnce(new Error('offline'))
    expect(await mod.getUsdEurRate()).toBe(mod.FALLBACK_USD_EUR)
    // Nächster Aufruf versucht es erneut (pending wurde zurückgesetzt)
    api.get.mockResolvedValueOnce({ data: { rate: 0.9 } })
    expect(await mod.getUsdEurRate()).toBe(0.9)
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('sanitisiert implausible Backend-Werte auf den Fallback', async () => {
    const { api, mod } = await freshModule()
    api.get.mockResolvedValue({ data: { rate: 92 } })
    expect(await mod.getUsdEurRate()).toBe(mod.FALLBACK_USD_EUR)
  })
})
