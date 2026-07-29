// Sprechkarte: der Gesprächsablauf eines Telefonleitfadens, zum Sprechen statt
// Vorlesen. Nur für den Kanal Telefon — bei E-Mail und LinkedIn schreibt man den
// Text, da erübrigt sich eine Sprechhilfe (der Knopf erscheint dort nicht).
//
// Der Aufbau folgt dem, was in einem Kaltanruf zählt:
//
//   1. Platzhalter oben: was man VOR dem Wählen wissen muss.
//   2. Links der Ablauf, rechts die Einwände — NEBENEINANDER, nicht untereinander.
//      Einwände kommen unvorhersehbar; sie müssen sichtbar sein, ohne dass man am
//      Ablauf vorbeiscrollt und die Stelle verliert, an der man gerade spricht.
//   3. Der Einstieg steht WÖRTLICH und groß, ohne Stichworte. Den ersten Satz
//      improvisiert man nicht, und Stichworte wären dort Rauschen in der Sekunde,
//      in der man sie am wenigsten braucht.
//   4. Danach je Satz eine Sprechlinie: Stichworte groß, der Satz klein daneben.
//      Gepaart, nicht in zwei getrennten Blöcken — sonst weiß man nicht, welches
//      Stichwort zu welchem Satz gehört, und damit nicht, wo man ist.
//   5. Fragen immer wörtlich: eine umformulierte Frage wird unpräzise.
//   6. Einwände als Sprungmarken (ein Wort), Antwort-Stichworte sofort sichtbar,
//      der ganze Wortlaut einen Klick entfernt. Acht ausformulierte Zitate liest
//      im Gespräch niemand.
import { useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import Icon from '../../components/Icon'
import type { OutreachTemplate } from '../../types'
import { buildSpeakingCard, type SpeakingLine } from './speakingCard'

interface Props {
  template: OutreachTemplate
  onClose: () => void
}

/** Eine Sprechlinie: entweder wörtlich (Einstieg, Fragen) oder Stichworte + Satz. */
function Zeile({ zeile, wortwoertlich, bitte }: {
  zeile: SpeakingLine
  wortwoertlich: boolean
  /** Die Abschlussfrage — die eine Bitte, die knapp und klar sein muss. */
  bitte: boolean
}) {
  // Wörtlich: der Satz selbst ist der Inhalt, nicht die Rückfallebene. Auch dann,
  // wenn sich aus dem Satz nichts Brauchbares verdichten ließ (leere Stichworte) —
  // „Dann rechnen wir." ist als Satz besser als jede Zerlegung.
  if (wortwoertlich || zeile.frage || zeile.stichworte.length === 0) {
    return (
      <p className={`text-[15px] leading-relaxed break-words ${
        zeile.frage
          ? `border-l-2 pl-2.5 ${bitte
            ? 'border-accent text-text font-medium'
            : 'border-accent/50 text-text'}`
          : 'text-text'
      }`}
      >
        {zeile.satz}
      </p>
    )
  }
  return (
    <div className="break-words">
      <p className="text-[15px] leading-snug text-text">
        {zeile.stichworte.map((w, k) => (
          <span key={k}>
            {k > 0 && <span className="text-text-muted font-normal"> · </span>}
            <span className={/^\[\w+\]$/.test(w) ? 'text-warning font-medium' : 'font-medium'}>
              {w}
            </span>
          </span>
        ))}
      </p>
      {/* Die Rettung, wenn der Faden reißt — direkt an ihren Stichworten. */}
      <p className="text-[11px] leading-snug text-text-muted mt-0.5">{zeile.satz}</p>
    </div>
  )
}

export default function SpeakingCardDialog({ template, onClose }: Props) {
  const karte = useMemo(() => buildSpeakingCard(template.body), [template.body])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7
                      max-w-[1120px] w-full mx-4 animate-modal-in max-h-[92vh] flex flex-col">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="min-w-0">
            <h3 className="md-title-emph text-text break-words">{template.title}</h3>
            <p className="text-xs text-text-muted">Sprechkarte · Telefon</p>
          </div>
          <button onClick={onClose} aria-label="Schließen"
                  className="md-state shrink-0 w-9 h-9 grid place-items-center rounded-full text-text-muted">
            <Icon name="close" size={18} />
          </button>
        </div>

        <p className="text-xs text-text-muted mb-3">
          Fett gesetzt wird gesprochen, klein daneben steht die Rettung. Der Einstieg
          und jede Frage stehen wörtlich da — die sagt man genau so.
        </p>

        {/* Was man vor dem Wählen wissen muss */}
        {karte.platzhalter.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-text-muted mr-1">Vorher wissen:</span>
            {karte.platzhalter.map((p) => (
              <span key={p} className="text-[11px] px-2 py-0.5 rounded-full
                                       bg-warning/10 text-warning font-medium">
                {p}
              </span>
            ))}
          </div>
        )}

        {/* Ab lg scrollt JEDE SPALTE für sich (der Elternteil nicht mehr): Wer einen
            Einwand nachschlägt, darf die Sprechstelle im Ablauf nicht verlieren.
            Darunter bleibt es ein gemeinsamer Scroll — nebeneinander ist da kein
            Platz. */}
        <div className="flex-1 min-h-0 overflow-y-auto pr-1
                        lg:overflow-hidden lg:grid lg:grid-cols-[1fr_360px] lg:gap-7">
          {/* Links: der Ablauf */}
          <div className="min-w-0 lg:h-full lg:overflow-y-auto lg:pr-2">
            {karte.schritte.length === 0 ? (
              <p className="text-sm text-text-muted py-6 text-center">
                Aus dieser Vorlage lässt sich kein Ablauf ableiten.
              </p>
            ) : (
              <ol className="relative">
                {karte.schritte.map((schritt, i) => (
                  <li key={i} className="relative pl-9 pb-5 last:pb-0">
                    {/* Verbindungslinie: macht aus Kästen einen Ablauf. Nicht beim
                        letzten Schritt, sonst zeigt sie ins Leere. */}
                    {i < karte.schritte.length - 1 && (
                      <span className="absolute left-[13px] top-7 bottom-0 w-px bg-border"
                            aria-hidden="true" />
                    )}
                    <span className="absolute left-0 top-0 w-[27px] h-[27px] rounded-full
                                     bg-md-secondary-container text-on-secondary-container
                                     text-xs font-semibold grid place-items-center">
                      {i + 1}
                    </span>
                    <div className="flex items-baseline gap-2 mb-2 pt-1">
                      <h4 className="text-sm font-semibold text-text">{schritt.titel}</h4>
                      {schritt.wortwoertlich && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full
                                         bg-accent/15 text-accent font-medium">
                          wörtlich
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      {schritt.zeilen.map((zeile, k) => (
                        <Zeile
                          key={k}
                          zeile={zeile}
                          wortwoertlich={!!schritt.wortwoertlich}
                          bitte={zeile.satz === karte.abschlussfrage}
                        />
                      ))}
                    </div>

                    {/* Regie-Anweisung NACH den Sprechzeilen: Erst grüßt und fragt
                        man, dann verzweigt man. Oben stand sie chronologisch falsch
                        (im Browser gesehen). Warnton statt Akzent, weil Akzent hier
                        schon „das sagen" bedeutet — dieselbe Farbe hätte zweimal
                        Verschiedenes gemeint. */}
                    {schritt.hinweis && (
                      <div className="mt-2.5 flex gap-2 items-start border-l-2 border-warning/50
                                      bg-warning/5 pl-2 py-1 rounded-r">
                        <span className="text-[10px] uppercase tracking-wide text-warning/80
                                         font-semibold shrink-0 pt-[3px]">
                          Regie
                        </span>
                        <p className="text-xs text-warning/90 break-words">{schritt.hinweis}</p>
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* Rechts: die Einwände. Eigene Spalte, weil sie unvorhersehbar kommen —
              im Ablauf darunter müsste man beim Einwand die Sprechstelle verlassen. */}
          {karte.einwaende.length > 0 && (
            <div className="mt-6 pt-5 border-t border-border lg:mt-0 lg:pt-0 lg:border-t-0
                            lg:border-l lg:pl-6 min-w-0 lg:h-full lg:overflow-y-auto">
              <h4 className="text-sm font-semibold text-text mb-1">Wenn jemand einwendet</h4>
              <p className="text-[11px] text-text-muted mb-3">
                Marke erkennen, Stichworte sagen. Klick zeigt den Wortlaut.
              </p>
              <div className="space-y-1.5">
                {karte.einwaende.map((e, i) => (
                  <details key={i} className="group border border-border rounded-card
                                              bg-surface/50 overflow-hidden">
                    <summary className="md-state cursor-pointer list-none p-2.5">
                      <div className="flex items-center gap-1.5">
                        <Icon
                          name="chevronRight"
                          size={13}
                          className="shrink-0 text-text-muted transition-transform
                                     duration-short ease-spring group-open:rotate-90"
                        />
                        <span className="text-sm font-semibold text-accent break-words">
                          {e.label}
                        </span>
                      </div>
                      <p className="text-[13px] text-text leading-snug mt-1 pl-[19px] break-words">
                        {e.stichworte.map((w, k) => (
                          <span key={k}>
                            {k > 0 && <span className="text-text-muted"> · </span>}
                            <span className="font-medium">{w}</span>
                          </span>
                        ))}
                      </p>
                    </summary>
                    <div className="px-2.5 pb-2.5 pl-[31px]">
                      {/* Zitat nur, wenn die Marke NICHT schon der ganze Einwand ist —
                          bei „Zu teuer" stünde sonst zweimal dasselbe. */}
                      {!e.einwand.startsWith(e.label) && (
                        <p className="text-[11px] text-text-muted italic break-words mb-1">
                          „{e.einwand}“
                        </p>
                      )}
                      <p className="text-[12px] text-text leading-snug break-words">
                        {e.antwort}
                      </p>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end mt-4">
          <button onClick={onClose} className="btn-secondary">Schließen</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
