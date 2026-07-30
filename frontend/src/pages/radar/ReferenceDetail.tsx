// Detail-Seite eines Referenzkunden — alles, was für die Ansprache gebraucht wird.
//
// Aufbau nach Nutzen im Gespräch: erst der Anknüpfungspunkt (welche Systeme, mit
// Beleg), dann das Angebot (welche Bausteine passen), dann die Kontaktwege. Der Score
// steht dabei, aber klein: Er hat die Firma auf diese Seite gebracht, für das Gespräch
// trägt er nichts bei.
//
// **Jeder angereicherte Wert zeigt seine Herkunft.** Website aus dem Verzeichnis
// verlinkt ist stärker belegt als eine über den Namen aufgelöste; ein Geschäftsführer
// aus dem Impressum trägt sein Zitat. Ohne diese Kennzeichnung wäre nicht mehr
// unterscheidbar, was gesichert ist und was eine Ableitung.
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import Icon from '../../components/Icon'
import LoadingIndicator from '../../components/LoadingIndicator'
import { useAppNavigate } from '../../utils/transitions'
import {
  getMarketBausteine,
  getMarketProducts,
  getMarketReferenceCompany,
  referencesToPipeline,
  updateMarketReference,
  type MarketBaustein,
  type MarketProduct,
  type MarketReferenceDetail,
} from '../../api/market'
import { httpHref } from '../../utils/safeHref'
import RadarShell from './RadarShell'
import ProductDialog from './ProductDialog'

const TEIL_LABEL: Record<string, string> = {
  mehrfachnutzung: 'nutzt mehrere Systeme',
  baustein: 'Baustein passt',
  umfeld: 'Umfeld (Produkt-Score)',
  ansprechbar: 'Website bekannt',
}

const ORG_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlicher Träger',
  konzern: 'Konzern',
  mittelstand: 'Mittelstand',
  unbekannt: 'Typ offen',
}

/** Herkunft der Website in Worten — „aufgelöst" ist schwächer belegt als „verlinkt". */
const WEBSITE_HERKUNFT: Record<string, string> = {
  verlinkt: 'im Referenzverzeichnis verlinkt',
  places: 'über den Firmennamen aufgelöst (Google Places, Namensprüfung bestanden)',
}

function Feld({ label, children, hinweis }: {
  label: string
  children: React.ReactNode
  hinweis?: string
}) {
  return (
    <div className="flex gap-3 py-1.5 border-b border-border/40 last:border-0">
      <dt className="text-text-muted text-xs w-36 shrink-0 pt-0.5">{label}</dt>
      <dd className="text-sm text-text break-words min-w-0">
        {children}
        {hinweis && <span className="block text-[11px] text-text-muted">{hinweis}</span>}
      </dd>
    </div>
  )
}

export default function ReferenceDetail() {
  const { key = '' } = useParams()
  const navigate = useAppNavigate()
  const [d, setD] = useState<MarketReferenceDetail | null>(null)
  const [laedt, setLaedt] = useState(true)
  const [busy, setBusy] = useState(false)
  const [bausteine, setBausteine] = useState<MarketBaustein[]>([])
  // Der Dialog braucht das ganze Produkt. Einmal laden, nicht je System — dieselbe
  // Entscheidung wie in der Kundenliste.
  const [produkte, setProdukte] = useState<Map<string, MarketProduct>>(new Map())
  const [info, setInfo] = useState<MarketProduct | null>(null)

  const laden = useCallback(async () => {
    setLaedt(true)
    try {
      setD(await getMarketReferenceCompany(key))
    } catch {
      toast.error('Firma konnte nicht geladen werden.')
    }
    setLaedt(false)
  }, [key])

  useEffect(() => { void laden() }, [laden])
  // Bausteine einmal laden — der Info-Dialog ordnet sie selbst zu.
  useEffect(() => {
    getMarketBausteine().then(setBausteine).catch(() => undefined)
    getMarketProducts({}).then((ps) => setProdukte(new Map(ps.map((x) => [x.id, x]))))
      .catch(() => undefined)
  }, [])

  const uebernehmen = async () => {
    if (!d) return
    setBusy(true)
    try {
      // Alle Nennungen mitgeben: Die Namens-Dedup legt EINEN Lead an und hängt die
      // Briefings der weiteren Systeme an.
      const r = await referencesToPipeline(d.reference_ids, true)
      const neu = r.created.length
      toast.success(neu ? 'Als Lead angelegt.' : 'Mit vorhandenem Lead verknüpft.')
      await laden()
    } catch {
      toast.error('Übernahme fehlgeschlagen.')
    }
    setBusy(false)
  }

  const verwerfen = async () => {
    if (!d) return
    setBusy(true)
    try {
      await Promise.all(d.reference_ids.map(
        (id) => updateMarketReference(id, { status: 'verworfen' })))
      toast.success('Verworfen.')
      await laden()
    } catch {
      toast.error('Konnte nicht verworfen werden.')
    }
    setBusy(false)
  }

  if (laedt) return <RadarShell><LoadingIndicator /></RadarShell>
  if (!d) {
    return (
      <RadarShell>
        <p className="text-sm text-text-muted">Diese Firma gibt es nicht (mehr).</p>
      </RadarShell>
    )
  }

  const angereichert = d.contact_checked_at
  const beleg = (feld: string) => {
    const b = d.contact_evidence?.[feld]
    if (!b) return undefined
    return `Quelle: ${b.quelle}${b.zitat ? `\n„${b.zitat}"` : ''}`
  }

  return (
    <RadarShell>
      <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => navigate('/radar/kunden', { back: true })}
            className="text-xs text-accent mb-1"
          >
            ← Referenzkunden
          </button>
          <h2 className="md-display text-text break-words">{d.company}</h2>
          <p className="text-sm text-text-muted">
            {ORG_LABEL[d.orgtyp] ?? d.orgtyp} · nutzt {d.systeme}{' '}
            {d.systeme === 1 ? 'System' : 'Systeme'}
            {d.status === 'in_pipeline' && ' · als Lead übernommen'}
            {d.status === 'verworfen' && ' · verworfen'}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {d.rainmaker_lead_id && (
            <button
              type="button"
              onClick={() => navigate(`/pipeline/leads/${d.rainmaker_lead_id}`)}
              className="btn-secondary text-sm"
            >
              → Lead ansehen
            </button>
          )}
          {d.status !== 'in_pipeline' && (
            <button type="button" className="btn-primary text-sm" disabled={busy}
                    onClick={uebernehmen}>
              in die Pipeline
            </button>
          )}
          {d.status === 'neu' && (
            <button type="button" className="btn-secondary text-sm" disabled={busy}
                    onClick={verwerfen}>
              verwerfen
            </button>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-5">
        <div className="space-y-5 min-w-0">
          {/* Der Anknüpfungspunkt: welche Software, und woher wir das wissen. */}
          <section className="card p-4">
            <h3 className="text-sm font-medium text-text mb-1">Setzt ein</h3>
            <p className="text-[11px] text-text-muted mb-3">
              Nachweislich — der Hersteller führt die Firma selbst in seinem
              Referenzverzeichnis. Das ist der Gesprächseinstieg.
            </p>
            <ul className="space-y-2.5">
              {d.produkte.map((s) => (
                <li key={s.reference_id} className="border-l-2 border-accent/40 pl-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-text min-w-0 break-words">{s.produkt}</p>
                    {/* Info-Fenster: was und wie sich an dieser Software verbessern
                        lässt. Am System, nicht an der Firma — die Antwort hängt an der
                        Software. */}
                    {produkte.get(s.product_id) && (
                      <button
                        type="button"
                        onClick={() => setInfo(produkte.get(s.product_id) ?? null)}
                        title="Dossier: Verbesserungspotenzial, Baustein, Score"
                        aria-label={`Dossier zu ${s.produkt} öffnen`}
                        className="md-state shrink-0 w-7 h-7 grid place-items-center rounded-lg
                                   text-text-muted hover:text-accent"
                      >
                        <Icon name="info" size={15} />
                      </button>
                    )}
                  </div>
                  {/* Anbieter verlinkt, wenn die Website bekannt ist (137 von 142) —
                      sonst nur der Name statt eines Links ins Leere. */}
                  {/* Nur http(s) als href — die Website stammt aus der
                      Hersteller-Anreicherung, `source_url` aus der Katalogdatei
                      (s. utils/safeHref). */}
                  <p className="text-[11px] text-text-muted">
                    {httpHref(s.website) ? (
                      <a href={httpHref(s.website)} target="_blank" rel="noopener noreferrer"
                         className="text-accent">
                        {s.hersteller}
                      </a>
                    ) : s.hersteller}
                  </p>
                  {s.baustein_titel && (
                    <p className="text-[11px] text-accent/90">
                      → Baustein {s.baustein_nr}: {s.baustein_titel}
                    </p>
                  )}
                  {httpHref(s.source_url) && (
                    <a href={httpHref(s.source_url)} target="_blank" rel="noopener noreferrer"
                       className="text-[11px] text-accent inline-flex items-center gap-1 mt-0.5">
                      <Icon name="users" size={12} /> Beleg im Verzeichnis
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </section>

          {/* Das Angebot. */}
          {d.bausteine.length > 0 && (
            <section className="card p-4">
              <h3 className="text-sm font-medium text-text mb-1">Aufsatzlösung anbieten</h3>
              <p className="text-[11px] text-text-muted mb-3">
                Aus dem Recherchekatalog: Bausteine, die auf die eingesetzte Software passen.
              </p>
              <ul className="space-y-3">
                {d.bausteine.map((b) => (
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
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <div className="space-y-5 min-w-0">
          {/* Kontaktwege — mit Herkunft, damit nichts wie eine Gewissheit aussieht,
              was eine Ableitung ist. */}
          <section className="card p-4">
            <h3 className="text-sm font-medium text-text mb-1">Kontakt</h3>
            <p className="text-[11px] text-text-muted mb-2">
              {angereichert
                ? `angereichert am ${new Date(angereichert).toLocaleDateString('de-DE')}`
                : 'noch nicht angereichert — Website, Impressum und Telefon fehlen'}
            </p>
            <dl>
              {d.website && (
                <Feld label="Website" hinweis={WEBSITE_HERKUNFT[d.website_source ?? '']}>
                  {httpHref(d.website) ? (
                    <a href={httpHref(d.website)} target="_blank" rel="noopener noreferrer"
                       className="text-accent">
                      {d.website.replace(/^https?:\/\//, '')}
                    </a>
                  ) : (
                    // Wert anzeigen, aber nicht klickbar machen: Der Wert ist Information,
                    // der Link wäre das Risiko.
                    <span className="break-all">{d.website}</span>
                  )}
                </Feld>
              )}
              {d.email && (
                <Feld label="E-Mail">
                  <a href={`mailto:${d.email}`} className="text-accent" title={beleg('email')}>
                    {d.email}
                  </a>
                  {d.email_status && d.email_status !== 'valid' && (
                    <span className="text-xs text-warning"> · {d.email_status}</span>
                  )}
                </Feld>
              )}
              {d.phone && (
                <Feld label="Telefon">
                  <a href={`tel:${d.phone.replace(/\s/g, '')}`} className="text-accent"
                     title={beleg('phone')}>
                    {d.phone}
                  </a>
                </Feld>
              )}
              {d.decision_maker && (
                <Feld label="Geschäftsführung">
                  <span title={beleg('decision_maker')}>{d.decision_maker}</span>
                </Feld>
              )}
              {d.employee_count != null && (
                <Feld label="Mitarbeitende">{d.employee_count}</Feld>
              )}
              {d.address && <Feld label="Adresse">{d.address}</Feld>}
            </dl>
            {!d.website && !d.email && !d.phone && (
              <p className="text-xs text-text-muted">
                Aus einer Logo-Wand geerntet — dort steht der Name, keine Adresse. Die
                Anreicherung löst die Website über den Firmennamen auf und liest dann
                das Impressum; sie läuft über die Kommandozeile, weil die Auflösung
                Abfragekosten hat.
              </p>
            )}
          </section>

          {/* Der Score zuletzt und klein: Er hat die Firma hierher gebracht, für das
              Gespräch trägt er nichts bei. */}
          <section className="card p-4">
            <h3 className="text-sm font-medium text-text mb-2">
              Score {d.score}
              <span className="text-[11px] font-normal text-text-muted"> · keine Umsatzprognose</span>
            </h3>
            <dl className="text-xs space-y-1">
              {Object.entries(d.score_teile).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <dt className={v > 0 ? 'text-text-muted' : 'text-text-muted/50'}>
                    {TEIL_LABEL[k] ?? k}
                  </dt>
                  <dd className={v > 0 ? 'text-text tabular-nums' : 'text-text-muted/50 tabular-nums'}>
                    +{v}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </div>
      {info && (
        <ProductDialog
          product={info}
          bausteine={bausteine}
          kontext="kunde"
          onClose={() => setInfo(null)}
          onChanged={(next) => {
            setProdukte((m) => new Map(m).set(next.id, next))
            setInfo(next)
          }}
        />
      )}
    </RadarShell>
  )
}
