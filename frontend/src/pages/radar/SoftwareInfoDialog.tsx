// „Was kann ich an dieser Software verbessern — und wie?"
//
// **Der Text ist nicht neu geschrieben, sondern die vorhandene Recherche sichtbar
// gemacht.** Die Antwort steckt schon in den Katalogfeldern, lag aber verstreut und
// teilweise gar nicht in der Oberfläche: `pains` sagt, was heute Handarbeit ist, `ki`
// was sich automatisieren lässt, `integration`/`int_level` WIE man rankommt, und die
// Bausteine, welche Aufsatzlösung dafür bereitliegt. Ein KI-generierter Text pro
// Produkt wäre teurer, langsamer und würde riskieren, etwas zu behaupten, was die
// Recherche nicht sagt.
//
// Reihenfolge = die Fragen, die man in dieser Folge stellt:
//   1. Was ist heute Handarbeit?      (der Schmerz)
//   2. Was lässt sich automatisieren? (die Idee)
//   3. Welcher Baustein passt?        (das Angebot, mit Aufwand und Vorsicht)
//   4. Wie kommt man ran?             (Integration — die eigentliche „wie"-Frage)
//   5. Worauf achten?                 (Hersteller besetzt es selbst)
//   6. Welcher Anlass?                (Regulatorik, Marktplatz)
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import Icon from '../../components/Icon'
import type { MarketBaustein } from '../../api/market'

/** Was der Dialog braucht. Absichtlich strukturell: `MarketProduct` (Hersteller-Tab)
 *  und `MarketReferenceSystem` (Kundendetail) erfüllen das beide. */
export interface SoftwareInfo {
  produkt?: string | null
  hersteller?: string | null
  catalog_id?: string | null
  website?: string | null
  ref_url?: string | null
  kategorie?: string | null
  pains?: string[]
  ki?: string[]
  nutzen?: string | null
  integration?: string | null
  int_level?: string | null
  notiz?: string | null
  reg?: string[]
  marketplace?: boolean
  mp_evidence?: string[]
  self_compete?: boolean
  zielgruppe?: string | null
  nutzer?: string[]
  prozesse?: string[]
  refs?: number
}

const AUFWAND_LABEL: Record<string, string> = {
  leicht: 'leicht — offene Schnittstelle, schneller erster Proof',
  mittel: 'mittel',
  schwer: 'schwer — Zugang ist der Engpass, nicht die Idee',
}

function Abschnitt({ nr, titel, children }: {
  nr: number
  titel: string
  children: React.ReactNode
}) {
  return (
    <section className="relative pl-8 pb-4 last:pb-0">
      <span className="absolute left-0 top-0 w-[24px] h-[24px] rounded-full
                       bg-md-secondary-container text-on-secondary-container
                       text-[11px] font-semibold grid place-items-center">
        {nr}
      </span>
      <h4 className="text-sm font-semibold text-text mb-1 pt-0.5">{titel}</h4>
      {children}
    </section>
  )
}

interface Props {
  info: SoftwareInfo
  /** Alle Bausteine — die Zuordnung macht der Dialog selbst (s. unten). */
  bausteine: MarketBaustein[]
  onClose: () => void
}

export default function SoftwareInfoDialog({ info, bausteine, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Zuordnung Produkt → Bausteine über `catalog_ids`. Eine Stelle im Frontend,
  // spiegelt `market_reference_pipeline.bausteine_fuer` im Backend — die Zuordnung
  // selbst kommt aus dem Recherchekatalog und wird hier nur gelesen.
  const passend = info.catalog_id
    ? bausteine.filter((b) => (b.catalog_ids ?? []).includes(info.catalog_id!))
    : []

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 animate-md-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div className="relative bg-surface-high rounded-dialog shadow-elev-3 p-5 sm:p-7
                      max-w-[720px] w-full mx-4 animate-modal-in max-h-[92vh] flex flex-col">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="min-w-0">
            <h3 className="md-title-emph text-text break-words">{info.produkt}</h3>
            <p className="text-xs text-text-muted break-words">
              {info.website ? (
                <a href={info.website} target="_blank" rel="noopener noreferrer"
                   className="text-accent">
                  {info.hersteller}
                </a>
              ) : info.hersteller}
              {info.kategorie && ` · ${info.kategorie}`}
            </p>
          </div>
          <button onClick={onClose} aria-label="Schließen"
                  className="md-state shrink-0 w-9 h-9 grid place-items-center rounded-full text-text-muted">
            <Icon name="close" size={18} />
          </button>
        </div>

        <p className="text-xs text-text-muted mb-4">
          Was sich an dieser Software verbessern lässt — aus der Recherche, nicht neu
          formuliert.
        </p>

        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
          {(info.pains ?? []).length > 0 && (
            <Abschnitt nr={1} titel="Heute Handarbeit">
              <ul className="text-sm text-text space-y-1">
                {(info.pains ?? []).map((x, i) => (
                  <li key={i} className="border-l-2 border-warning/40 pl-2">{x}</li>
                ))}
              </ul>
            </Abschnitt>
          )}

          {(info.ki ?? []).length > 0 && (
            <Abschnitt nr={2} titel="Lässt sich automatisieren">
              <ul className="text-sm text-text space-y-1">
                {(info.ki ?? []).map((x, i) => (
                  <li key={i} className="border-l-2 border-accent/50 pl-2">{x}</li>
                ))}
              </ul>
              {info.nutzen && (
                <p className="text-xs text-text-muted mt-1.5">
                  <span className="text-text-muted/70">Was das bringt: </span>{info.nutzen}
                </p>
              )}
            </Abschnitt>
          )}

          <Abschnitt nr={3} titel="Aufsatzlösung">
            {passend.length > 0 ? (
              <ul className="space-y-3">
                {passend.map((b) => (
                  <li key={b.nr}>
                    <p className="text-sm text-text">Baustein {b.nr}: {b.titel}</p>
                    {b.was && <p className="text-xs text-text-muted mt-0.5">{b.was}</p>}
                    {b.warum && (
                      <p className="text-[11px] text-text-muted mt-1">
                        <span className="text-accent/80">Warum jetzt: </span>{b.warum}
                      </p>
                    )}
                    {b.aufwand && (
                      <p className="text-[11px] text-text-muted">Aufwand: {b.aufwand}</p>
                    )}
                    {b.vorsicht && (
                      <p className="text-[11px] text-warning/90 mt-0.5">
                        Vorsicht: {b.vorsicht}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              // 37 der 142 Produkte haben keinen zugeordneten Baustein. Das ehrlich
              // sagen — die Idee aus 1 und 2 steht trotzdem.
              <p className="text-xs text-text-muted">
                Kein Baustein aus dem Katalog zugeordnet. Die Idee oben trägt trotzdem —
                sie ist nur nicht als fertiger Baustein modelliert.
              </p>
            )}
          </Abschnitt>

          {info.integration && (
            <Abschnitt nr={4} titel="Wie man rankommt">
              <p className="text-sm text-text">{info.integration}</p>
              {info.int_level && (
                <p className="text-[11px] text-text-muted mt-1">
                  Integrationsaufwand: {AUFWAND_LABEL[info.int_level] ?? info.int_level}
                </p>
              )}
            </Abschnitt>
          )}

          {(info.self_compete || (info.reg ?? []).length > 0 || info.marketplace) && (
            <Abschnitt nr={5} titel="Worauf achten">
              {info.self_compete && (
                <p className="text-sm text-warning/90 mb-1.5">
                  Der Hersteller besetzt diesen Use Case selbst — nur mit einer Nische
                  oder als Partner sinnvoll.
                </p>
              )}
              {(info.reg ?? []).length > 0 && (
                <p className="text-xs text-text-muted">
                  <span className="text-text-muted/70">Terminierter Anlass: </span>
                  {(info.reg ?? []).join(', ')}
                </p>
              )}
              {info.marketplace && (
                <p className="text-xs text-text-muted">
                  <span className="text-text-muted/70">Marktplatz/Partnerprogramm: </span>
                  {(info.mp_evidence ?? []).join(', ') || 'vorhanden'} — Listing statt
                  Einzelvertrieb prüfen.
                </p>
              )}
            </Abschnitt>
          )}

          {(info.zielgruppe || (info.nutzer ?? []).length > 0
            || (info.prozesse ?? []).length > 0) && (
            <Abschnitt nr={6} titel="Wer damit arbeitet">
              {info.zielgruppe && <p className="text-sm text-text">{info.zielgruppe}</p>}
              {(info.nutzer ?? []).length > 0 && (
                <p className="text-xs text-text-muted mt-1">
                  <span className="text-text-muted/70">Tägliche Nutzer: </span>
                  {(info.nutzer ?? []).join(', ')}
                </p>
              )}
              {(info.prozesse ?? []).length > 0 && (
                <p className="text-xs text-text-muted">
                  <span className="text-text-muted/70">Prozesse: </span>
                  {(info.prozesse ?? []).join(', ')}
                </p>
              )}
            </Abschnitt>
          )}

          {info.notiz && (
            <div className="mt-2 pt-3 border-t border-border">
              <p className="text-[11px] text-text-muted mb-1">Notiz aus der Recherche</p>
              <p className="text-xs text-text-muted italic">{info.notiz}</p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 mt-4 flex-wrap">
          <div className="flex items-center gap-3 text-xs">
            {info.website && (
              <a href={info.website} target="_blank" rel="noopener noreferrer"
                 className="text-accent inline-flex items-center gap-1">
                <Icon name="globe" size={13} /> Anbieter
              </a>
            )}
            {info.ref_url && (
              <a href={info.ref_url} target="_blank" rel="noopener noreferrer"
                 className="text-accent inline-flex items-center gap-1">
                <Icon name="users" size={13} />
                Referenzverzeichnis{info.refs ? ` (~${info.refs})` : ''}
              </a>
            )}
          </div>
          <button onClick={onClose} className="btn-secondary text-sm">Schließen</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
