// Sprechkarte: der Gesprächsablauf einer Vorlage, zum Sprechen statt Vorlesen.
//
// Aufbau folgt dem, was man im Gespräch braucht — in dieser Reihenfolge:
//   1. Platzhalter oben: was man VOR dem Wählen wissen muss.
//   2. Der Ablauf als numerierte Schritte mit Verbindungslinie: wo bin ich.
//   3. Stichworte groß, die Sätze klein darunter — man spricht an den Stichworten
//      und fällt auf den Satz zurück, wenn der Faden reißt.
//   4. Einwände als eigener Block: im Gespräch schlägt man sie nach, sie liegen
//      nicht im Sprechfluss.
//   5. Die Abschlussfrage ganz unten, wörtlich — die eine Bitte soll knapp sein.
import { useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import Icon from '../../components/Icon'
import type { OutreachTemplate } from '../../types'
import { CHANNEL_LABEL } from './constants'
import { buildSpeakingCard } from './speakingCard'

interface Props {
  template: OutreachTemplate
  onClose: () => void
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
                      max-w-[760px] w-full mx-4 animate-modal-in max-h-[90vh] flex flex-col">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="min-w-0">
            <h3 className="md-title-emph text-text break-words">{template.title}</h3>
            <p className="text-xs text-text-muted">
              Sprechkarte · {CHANNEL_LABEL[template.channel]}
            </p>
          </div>
          <button onClick={onClose} aria-label="Schließen"
                  className="md-state shrink-0 w-9 h-9 grid place-items-center rounded-full text-text-muted">
            <Icon name="close" size={18} />
          </button>
        </div>

        <p className="text-xs text-text-muted mb-4">
          Stichworte sprechen, nicht vorlesen. Der Satz darunter ist nur die Rettung,
          wenn der Faden reißt.
        </p>

        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
          {/* Was man vor dem Wählen wissen muss */}
          {karte.platzhalter.length > 0 && (
            <div className="mb-5 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-text-muted mr-1">Vorher wissen:</span>
              {karte.platzhalter.map((p) => (
                <span key={p} className="text-[11px] px-2 py-0.5 rounded-full
                                         bg-warning/10 text-warning font-medium">
                  {p}
                </span>
              ))}
            </div>
          )}

          {/* Der Ablauf */}
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
                  <h4 className="text-sm font-semibold text-text mb-1.5 pt-1">
                    {schritt.titel}
                  </h4>

                  {schritt.stichworte.length > 0 && (
                    <p className="text-base text-text leading-relaxed mb-2 break-words">
                      {schritt.stichworte.map((w, k) => (
                        <span key={k}>
                          {k > 0 && <span className="text-text-muted"> · </span>}
                          <span className={/^\[\w+\]$/.test(w)
                            ? 'text-warning font-medium' : 'font-medium'}>{w}</span>
                        </span>
                      ))}
                    </p>
                  )}

                  {schritt.hinweis && (
                    <p className="text-xs text-accent/90 border-l-2 border-accent/40 pl-2 mb-2">
                      {schritt.hinweis}
                    </p>
                  )}

                  {schritt.saetze.length > 0 && (
                    <ul className="space-y-0.5">
                      {schritt.saetze.map((satz, k) => (
                        <li key={k} className="text-[11px] text-text-muted break-words">
                          {satz}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          )}

          {/* Einwände: Nachschlagewerk, nicht Sprechfluss */}
          {karte.einwaende.length > 0 && (
            <div className="mt-6 pt-5 border-t border-border">
              <h4 className="text-sm font-semibold text-text mb-3">
                Wenn jemand einwendet
              </h4>
              <div className="space-y-2.5">
                {karte.einwaende.map((e, i) => (
                  <div key={i} className="border border-border rounded-card p-3 bg-surface/50">
                    <p className="text-sm text-text mb-1 break-words">
                      <span className="text-text-muted mr-1.5">„</span>
                      {e.einwand}
                      <span className="text-text-muted ml-0.5">“</span>
                    </p>
                    <p className="text-sm text-text leading-relaxed break-words">
                      <span className="text-accent mr-1.5" aria-hidden="true">→</span>
                      {e.stichworte.map((w, k) => (
                        <span key={k}>
                          {k > 0 && <span className="text-text-muted"> · </span>}
                          <span className="font-medium">{w}</span>
                        </span>
                      ))}
                    </p>
                    <p className="text-[11px] text-text-muted mt-1 break-words">{e.antwort}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Die eine Bitte — wörtlich */}
          {karte.abschlussfrage && (
            <div className="mt-6 pt-5 border-t border-border">
              <p className="text-[11px] text-text-muted mb-1">
                Wörtlich sagen — kurz halten:
              </p>
              <p className="text-base text-text font-medium break-words">
                {karte.abschlussfrage}
              </p>
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
