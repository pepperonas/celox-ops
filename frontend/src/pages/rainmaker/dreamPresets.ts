// Traumziel presets — researched 06/2026. Prices are realistic German list
// prices (base, rounded); specs are flavor for the hero card.
export interface DreamPreset {
  key: string
  name: string
  price: number
  emoji: string
  tagline: string
  specs: string[]
  /** Hero gradient (from → to). */
  colors: [string, string]
}

export const DREAM_PRESETS: DreamPreset[] = [
  {
    key: 'cayenne_turbo_e',
    name: 'Porsche Cayenne Turbo Electric',
    price: 165500,
    emoji: '🚙',
    tagline: 'Das stärkste Serien-SUV, das Porsche je gebaut hat — elektrisch.',
    specs: ['1.156 PS', '0–100 in 2,5 s', '617 km Reichweite'],
    colors: ['#1b2a4a', '#3d6bb3'],
  },
  {
    key: 'brabus_bodo',
    name: 'Brabus Bodo',
    price: 1200000,
    emoji: '🏎️',
    tagline: 'V12-Biturbo-Hyper-GT auf Vanquish-Basis. Einer von 77.',
    specs: ['1.000 PS V12', '360 km/h', 'limitiert auf 77'],
    colors: ['#2a1a1a', '#b3392e'],
  },
  {
    key: 'taycan_turbo_gt',
    name: 'Porsche Taycan Turbo GT',
    price: 245000,
    emoji: '⚡',
    tagline: 'Nürburgring-Rekordhalter unter den Serien-Elektroautos.',
    specs: ['1.108 PS', '0–100 in 2,3 s', '305 km/h'],
    colors: ['#1a2e2a', '#2e8b74'],
  },
  {
    key: '911_turbo_s',
    name: 'Porsche 911 Turbo S',
    price: 271500,
    emoji: '🏁',
    tagline: 'Die Ikone. Alltag und Rennstrecke in einem.',
    specs: ['711 PS', '0–100 in 2,5 s', '322 km/h'],
    colors: ['#2d2a1a', '#b39b2e'],
  },
  {
    key: 'amg_g63',
    name: 'Mercedes-AMG G 63',
    price: 186000,
    emoji: '🦍',
    tagline: 'Der Fels. V8-Biturbo im kantigsten Blech der Welt.',
    specs: ['585 PS V8', '0–100 in 4,4 s', 'Offroad-Legende'],
    colors: ['#1f1f24', '#5a5f6e'],
  },
  {
    key: 'custom',
    name: 'Eigenes Ziel',
    price: 100000,
    emoji: '🎯',
    tagline: 'Haus, Boot, Weltreise — dein Ziel, deine Regeln.',
    specs: ['frei konfigurierbar'],
    colors: ['#241a2e', '#7a4fb3'],
  },
]

export function presetByKey(key: string | null | undefined): DreamPreset {
  return DREAM_PRESETS.find((p) => p.key === key) ?? DREAM_PRESETS[0]
}

// ---------------------------------------------------------------------------
// Pure motivation math (mirrors the backend engine — kept tiny + testable).
// ---------------------------------------------------------------------------

/** 1.000 € = 1 km: converts an amount into "driving distance" toward the car. */
export function euroToKm(amount: number): number {
  return amount / 1000
}

/** Expected € toward the dream per weight-1.0 contact (one call). */
export function evPerContact(avgDealValue: number, savingsRatePct: number, contactsPerWin: number): number {
  if (contactsPerWin <= 0 || savingsRatePct <= 0) return 0
  return (avgDealValue * (savingsRatePct / 100)) / contactsPerWin
}

/** How many months earlier the goal lands if `amount` € drop in now, at the
 *  current pace (€/day). Infinity-safe: returns null without a pace. */
export function monthsEarlier(amount: number, pacePerDay: number): number | null {
  if (pacePerDay <= 0) return null
  return amount / (pacePerDay * 30.44)
}

/** Milestones along the road (fraction of the price → celebration). */
export const DREAM_MILESTONES: { at: number; icon: string; label: string }[] = [
  { at: 0.1, icon: '📋', label: 'Konfiguriert' },
  { at: 0.25, icon: '🛞', label: 'Felgen' },
  { at: 0.5, icon: '🎨', label: 'Lack & Karosserie' },
  { at: 0.75, icon: '🪑', label: 'Interieur' },
  { at: 1, icon: '🔑', label: 'Schlüsselübergabe' },
]
