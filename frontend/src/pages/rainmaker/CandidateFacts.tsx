// Darstellung der angereicherten Kandidaten-Fakten (ein Startseiten-Abruf im
// Backend, services/lead_enrichment.py). Rein präsentational und in beiden
// Import-Dialogen (Branchen-Suche + KI-Suche) verwendet.
import type { DiscoveredCandidate } from '../../types'

const PRIVACY: Record<string, { color: string; label: string }> = {
  gruen: { color: '#22c55e', label: 'Datenschutz: keine Auffälligkeit gefunden' },
  gelb: { color: '#f59e0b', label: 'Datenschutz: Auffälligkeit' },
  rot: { color: '#ef4444', label: 'Datenschutz: Pflichtangabe fehlt oder Tracker ohne Einwilligung' },
}

const SOCIAL_ICON: Record<string, string> = {
  linkedin: 'in', xing: 'X|', facebook: 'f', instagram: 'ig',
  youtube: 'yt', twitter: 'X', tiktok: 'tt', github: 'gh',
}

/** Farbiger Punkt für die Datenschutz-Ampel (mit belegtem Grund im Tooltip). */
export function PrivacyDot({ rating, hint }: { rating?: string | null; hint?: string | null }) {
  if (!rating) return null
  const p = PRIVACY[rating]
  if (!p) return null
  return (
    <span
      title={hint ? `${p.label} — ${hint}` : p.label}
      className="inline-block w-2 h-2 rounded-full shrink-0 align-middle"
      style={{ backgroundColor: p.color }}
    />
  )
}

/** Kurzbeschreibung + Tech-Stack + Social-Profile als kompakte Zweitzeile. */
export default function CandidateFacts({ c }: { c: DiscoveredCandidate }) {
  const socials = Object.entries(c.socials || {})
  const techs = c.technologies || []
  if (!c.description && !techs.length && !socials.length) return null
  return (
    <div className="mt-0.5 space-y-0.5">
      {c.description && (
        <p className="text-[11px] text-text-muted line-clamp-2" title={c.description}>
          {c.description}
        </p>
      )}
      {(techs.length > 0 || socials.length > 0) && (
        <div className="flex flex-wrap items-center gap-1">
          {techs.slice(0, 3).map((t) => (
            <span key={t} className="text-[10px] px-1 py-px rounded bg-surface-container text-text-muted">
              {t}
            </span>
          ))}
          {socials.map(([key, url]) => (
            <a
              key={key}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              title={`${key}: ${url}`}
              className="text-[10px] px-1 py-px rounded bg-surface-container text-accent hover:underline"
            >
              {SOCIAL_ICON[key] || key}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
