// Reine Helfer für die Website-Score-Darstellung (Farben/Labels/Trend).

export const RATING_COLORS: Record<string, string> = {
  gruen: '#22c55e', gelb: '#eab308', orange: '#f59e0b', rot: '#ef4444',
}
export const RATING_LABELS: Record<string, string> = {
  gruen: 'Sehr gut', gelb: 'Gut', orange: 'Verbesserungswürdig', rot: 'Kritisch',
}
export const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444', warning: '#f59e0b', info: '#60a5fa',
}
export const PRIORITY_ORDER = ['kritisch', 'hoch', 'niedrig'] as const

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return '#6b7280'
  if (score >= 80) return RATING_COLORS.gruen
  if (score >= 60) return RATING_COLORS.gelb
  if (score >= 40) return RATING_COLORS.orange
  return RATING_COLORS.rot
}

export function ratingLabel(rating: string | null | undefined): string {
  return (rating && RATING_LABELS[rating]) || '—'
}

/** Trend gegenüber der Voranalyse: {delta, dir}. */
export function scoreTrend(current: number, previous: number | null | undefined): {
  delta: number; dir: 'up' | 'down' | 'flat'
} {
  if (previous == null) return { delta: 0, dir: 'flat' }
  const delta = current - previous
  return { delta, dir: delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat' }
}
