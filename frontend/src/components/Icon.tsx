import { ICONS, type IconName } from './icons/catalog'

interface Props {
  name: IconName
  /**
   * Kantenlänge in px. Standard 20 — passt zur Zeilenhöhe unserer
   * `text-sm`/`text-xs`-Typo, ohne die Grundlinie zu sprengen. Für Hero-Momente
   * größere Werte setzen; die Strichbreite skaliert mit (siehe unten).
   */
  size?: number
  /** Aktiver Zustand: gefüllte Fassung, wenn das Icon eine hat (MD3-`fill`). */
  filled?: boolean
  className?: string
  /**
   * Nur setzen, wenn das Icon die EINZIGE Information ist und kein Label
   * daneben steht. Standard ist `aria-hidden` — ein Icon neben Text darf nicht
   * doppelt vorgelesen werden.
   */
  label?: string
}

/**
 * Eigenes Icon auf dem Material-Raster (24×24, Live-Area 20, Strich 2).
 *
 * **Strichbreite skaliert mit der Größe.** Material nennt das die
 * `opsz`-Achse: damit ein Icon bei 16 px nicht zu fett und bei 40 px nicht zu
 * dünn wirkt, bleibt die *optische* Breite gleich, statt die 2 dp stur zu
 * übernehmen. Hier als lineare Näherung — genau genug für die vier Größen, die
 * diese App benutzt, und ohne variable Fontdatei.
 *
 * **Farbe kommt immer aus `currentColor`.** Ein Icon erbt damit die Textfarbe
 * seines Kontextes und funktioniert in jedem Theme-Token — genau das, was ein
 * Emoji nicht kann.
 */
export default function Icon({ name, size = 20, filled, className = '', label }: Props) {
  const def = ICONS[name]
  if (!def) return null
  const useSolid = Boolean(filled && def.solid)
  const els = useSolid ? def.solid! : def.outline
  // 2 dp bei 24 px Kantenlänge, leicht angehoben für kleine und gesenkt für
  // große Darstellungen (Näherung der opsz-Achse).
  const stroke = Math.round((2 * (24 / size) ** 0.35) * 100) / 100

  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={`inline-block shrink-0 ${className}`}
      fill={useSolid ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth={useSolid ? 0 : stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      // Runde Enden: bewusste Wahl fuers Expressive-Scheme dieses Repos.
      aria-hidden={label ? undefined : true}
      role={label ? 'img' : undefined}
      aria-label={label}
      focusable="false"
    >
      {els.map((el, i) => {
        switch (el.t) {
          case 'p':
            return <path key={i} d={el.d} />
          case 'c':
            return <circle key={i} cx={el.cx} cy={el.cy} r={el.r} />
          case 'l':
            return <line key={i} x1={el.x1} y1={el.y1} x2={el.x2} y2={el.y2} />
          case 'r':
            return <rect key={i} x={el.x} y={el.y} width={el.w} height={el.h} rx={el.rx} />
        }
      })}
    </svg>
  )
}
