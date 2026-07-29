import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { animate as anime } from 'animejs'
import type { OutreachTemplate } from '../../types'
import { CATEGORY_LABEL, CHANNEL_LABEL, isOfferCategory } from './constants'
import { CARD_COLORS, cardColor, colorToStore } from './cardColors'
import Icon from '../../components/Icon'
import { cubic, DUR, EASE, prefersReducedMotion, T } from '../../utils/motionTokens'

interface Props {
  template: OutreachTemplate
  showChannel?: boolean   // in der Suchansicht (kanalübergreifend)
  onCopy: (t: OutreachTemplate) => void
  onEdit: (t: OutreachTemplate) => void
  onToggleFavorite: (t: OutreachTemplate) => void
  onDelete: (t: OutreachTemplate) => void
  onSpeak: (t: OutreachTemplate) => void
  onColor?: (t: OutreachTemplate, color: string | null) => void
  /** false = Nur-Lese-Ansicht (Verkäufer): Bearbeiten/Löschen/Farbe entfallen. */
  mayEdit?: boolean
  /** Verschieben ist nur in der unsortierten Kanal-Ansicht sinnvoll. */
  draggable?: boolean
  onMoveBy?: (t: OutreachTemplate, delta: number) => void
  onDragStartCard?: () => void
  onDropOnCard?: () => void
  /**
   * Verzögerung des Eintritts in Sekunden (Staffelung). Kommt gedeckelt aus
   * `staggerDelay` — bei 30 Karten dürfen die letzten nicht sekundenlang warten.
   */
  enterDelay?: number
}

/**
 * Vorlagen-Karte.
 *
 * **Kompakt als Standard, ein Klick klappt auf.** Vorher stand der Text
 * dreizeilig abgeschnitten in jeder Karte, mit einem „mehr anzeigen"-Link. Das
 * löste das falsche Problem: Zum Wiedererkennen genügen Titel und Betreff, und den
 * FERTIGEN Text mit eingesetzten Platzhaltern zeigt ohnehin der Kopier-Dialog. Der
 * Kartenkopf ist jetzt selbst der Schalter — kein zusätzlicher Textbaustein.
 */
export default function TemplateCard({
  template, showChannel, onCopy, onEdit, onToggleFavorite, onDelete, onSpeak,
  onColor, mayEdit = true, draggable, onMoveBy, onDragStartCard, onDropOnCard,
  enterDelay = 0,
}: Props) {
  const [open, setOpen] = useState(false)
  const [colorOpen, setColorOpen] = useState(false)
  // Kopier-Bestätigung: kurzer Zustand, den motion animiert (zustandsgebunden →
  // motion, s. Arbeitsteilung in utils/motionTokens.ts).
  const [copied, setCopied] = useState(false)
  const sternRef = useRef<HTMLButtonElement>(null)
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Timer aufräumen: Wird die Karte weggefiltert, während die Bestätigung läuft,
  // setzte der Timer sonst Zustand auf einer ausgehängten Komponente.
  useEffect(() => () => { if (copyTimer.current) clearTimeout(copyTimer.current) }, [])

  /**
   * Stern-Puls — ereignisgesteuerter Einmal-Effekt, also anime.js.
   *
   * Bewusst nur beim SETZEN, nicht beim Entfernen: Eine Belohnung für das
   * Wegnehmen wäre eine widersprüchliche Rückmeldung.
   */
  const pulseStar = (wirdFavorit: boolean) => {
    if (!wirdFavorit || !sternRef.current || prefersReducedMotion()) return
    anime(sternRef.current, {
      scale: [1, 1.45, 1],
      rotate: [0, -14, 0],
      duration: DUR.spatialFast,
      // Literale Kurve, nie eine CSS-Variable — die Web Animations API nimmt
      // keine (Repo-Regel, s. motionTokens.ts).
      ease: cubic(EASE.spatialFast),
    })
  }
  const t = template
  const farbe = cardColor(t.color)
  const text = t.body.replace(/^##\s+/gm, '').trim()

  const iconBtn = 'md-state w-11 h-11 sm:w-8 sm:h-8 grid place-items-center rounded-lg '
    + 'text-text-muted hover:text-text shrink-0'

  return (
    <motion.div
      // `layout` ist der Kern des Piloten: Wird umsortiert, GLEITET die Karte an
      // ihren neuen Platz statt zu springen. motion misst dafür vor und nach dem
      // Umbau — genau das, was `utils/useFlipOrder.ts` von Hand tut; hier braucht
      // es keine Zeile davon.
      layout
      // Eintritt gestaffelt, Austritt SOFORT: Wer einen Filter wegklickt, will
      // die alten Karten nicht noch einmal einzeln verabschieden.
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97, transition: T.effectFast }}
      transition={{ ...T.spatialDefault, delay: enterDelay }}
      draggable={draggable}
      onDragStart={(e) => {
        // Nur der Ziehpunkt startet — sonst löst jeder Klick auf die Karte einen
        // Drag aus und Textauswahl wird unmöglich.
        if (!draggable) return
        // `motion.div` überschreibt `onDragStart` mit dem Typ SEINER eigenen
        // Zieh-Geste (die hier nicht benutzt wird — natives HTML5-Drag bleibt).
        // Zur Laufzeit kommt trotzdem das DOM-Ereignis an; der Cast benennt das,
        // statt es zu verstecken. Fällt weg, sobald das Ziehen auf motion umgestellt
        // wird.
        const de = e as unknown as React.DragEvent
        de.dataTransfer.effectAllowed = 'move'
        onDragStartCard?.()
      }}
      onDragOver={(e) => { if (draggable) e.preventDefault() }}
      onDrop={(e) => { if (draggable) { e.preventDefault(); onDropOnCard?.() } }}
      className={`border rounded-card flex flex-col transition-all duration-short
                  hover:shadow-elev-1 ${farbe.card}`}
    >
      {/* Kopf = Schalter. Ein <button> über die volle Breite, damit auch Tastatur
          und Screenreader auf-/zuklappen können. */}
      <div className="flex items-start gap-1 p-3 pb-2">
        {draggable && (
          <span className="md-state w-7 h-8 grid place-items-center rounded-lg cursor-grab
                           text-text-muted/60 shrink-0"
                title="Zum Verschieben ziehen" aria-hidden="true">
            <Icon name="drag" size={16} />
          </span>
        )}
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex-1 min-w-0 text-left"
        >
          <span className="flex flex-wrap items-center gap-1.5 mb-1">
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              isOfferCategory(t.category)
                ? 'bg-accent/10 text-accent'
                : 'bg-surface-container text-text-muted'
            }`}>{CATEGORY_LABEL[t.category]}</span>
            {showChannel && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-container text-text-muted">
                {CHANNEL_LABEL[t.channel]}
              </span>
            )}
            {t.usage_count > 0 && (
              <span className="text-[10px] text-text-muted" title="So oft kopiert">
                ↗ {t.usage_count}×
              </span>
            )}
          </span>
          <span className="flex items-center gap-1.5">
            <Icon name="chevronRight" size={14}
                  className={`text-text-muted transition-transform duration-short ease-spring
                              ${open ? 'rotate-90' : ''}`} />
            <span className="text-sm font-semibold text-text truncate">{t.title}</span>
          </span>
          {t.channel === 'email' && t.subject && (
            <span className="block text-xs text-text-muted truncate pl-5">{t.subject}</span>
          )}
        </button>
        <button
          ref={sternRef}
          onClick={() => { pulseStar(!t.is_favorite); onToggleFavorite(t) }}
          title={t.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}
          aria-label={t.is_favorite ? 'Favorit entfernen' : 'Als Favorit markieren'}
          className={iconBtn}
          style={{ color: t.is_favorite ? '#e0a500' : undefined }}
        >
          <Icon name="star" size={16} filled={t.is_favorite} />
        </button>
      </div>

      {/* Auf-/Zuklappen als Höhen-Animation. `AnimatePresence` braucht es, damit
          das Zuklappen überhaupt sichtbar wird — ohne wäre das Element beim
          nächsten Render einfach weg. `overflow-hidden` verhindert, dass der Text
          während der Bewegung aus der Karte ragt. */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={T.spatialFast}
            className="overflow-hidden"
          >
            <div className="px-3 pb-2">
              <p className="text-sm text-text-muted whitespace-pre-wrap break-words">{text}</p>
              {t.notes && (
                <p className="text-[11px] text-text-muted italic border-l-2 border-border pl-2 mt-2">
                  {t.notes}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Farbauswahl — erscheint nur auf Anforderung, damit sieben Punkte nicht
          dauerhaft in jeder Karte sitzen. */}
      {colorOpen && mayEdit && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {CARD_COLORS.map((c) => (
            <button
              key={c.key}
              onClick={() => { onColor?.(t, colorToStore(c.key)); setColorOpen(false) }}
              title={c.label}
              aria-label={c.label}
              className={`w-6 h-6 rounded-full ${c.dot} ${
                farbe.key === c.key ? 'ring-2 ring-text ring-offset-2 ring-offset-surface' : ''
              }`}
            />
          ))}
        </div>
      )}

      <div className="flex items-center gap-1 px-3 py-2 mt-auto border-t border-border/60">
        {/* Kopier-Bestätigung: Der Knopf zeigt kurz einen Haken. Die Aktion läuft
            sofort — die Animation hängt hinterher, nie davor. */}
        <button
          onClick={() => {
            onCopy(t)
            setCopied(true)
            if (copyTimer.current) clearTimeout(copyTimer.current)
            copyTimer.current = setTimeout(() => setCopied(false), 1100)
          }}
          className="btn-primary !py-2 flex-1 justify-center overflow-hidden"
        >
          <AnimatePresence initial={false} mode="wait">
            <motion.span
              key={copied ? 'ok' : 'label'}
              initial={{ y: copied ? 14 : -14, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: copied ? -14 : 14, opacity: 0 }}
              transition={T.effectFast}
              className="flex items-center gap-1.5"
            >
              {copied ? <><Icon name="celebrate" size={16} /> Kopiert</> : 'Kopieren'}
            </motion.span>
          </AnimatePresence>
        </button>
        <button onClick={() => onSpeak(t)} className={iconBtn}
                title="Sprechkarte: Ablauf mit Stichworten" aria-label="Sprechkarte öffnen">
          <Icon name="chat" size={17} />
        </button>
        {mayEdit && (
          <button onClick={() => setColorOpen((v) => !v)} className={iconBtn}
                  title="Farbe" aria-label="Farbe wählen">
            <Icon name="palette" size={17} />
          </button>
        )}
        {/* Verwaltung erscheint erst mit dem aufgeklappten Text. Sieben Knöpfe in
            jeder geschlossenen Karte waren das Gegenteil von aufgeräumt (im
            Browser gesehen) — und wer eine Vorlage sortiert oder bearbeitet, hat
            sie ohnehin geöffnet. Kopieren und Sprechkarte bleiben immer da. */}
        {mayEdit && open && (
          <>
            {onMoveBy && (
              // Pfeile als Ersatz fürs Ziehen: natives Drag & Drop funktioniert auf
              // Touch-Geräten nicht — ohne diese Knöpfe wäre Sortieren am Handy
              // unmöglich.
              <>
                <button onClick={() => onMoveBy(t, -1)} className={iconBtn}
                        title="Nach vorn" aria-label="Nach vorn verschieben">
                  <Icon name="chevronUp" size={17} />
                </button>
                <button onClick={() => onMoveBy(t, 1)} className={iconBtn}
                        title="Nach hinten" aria-label="Nach hinten verschieben">
                  <Icon name="chevronDown" size={17} />
                </button>
              </>
            )}
            <button onClick={() => onEdit(t)} className={iconBtn}
                    title="Bearbeiten" aria-label="Bearbeiten">
              <Icon name="pencil" size={17} />
            </button>
            <button onClick={() => onDelete(t)} className={`${iconBtn} hover:!text-danger`}
                    title="Löschen" aria-label="Löschen">
              <Icon name="trash" size={17} />
            </button>
          </>
        )}
      </div>
    </motion.div>
  )
}
