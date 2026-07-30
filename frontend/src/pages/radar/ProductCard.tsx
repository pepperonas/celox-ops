import Icon from '../../components/Icon'
import type { MarketProduct } from '../../api/market'

const REF_LABEL: Record<string, string> = {
  oeffentlich: 'öffentlich',
  teilweise: 'teilweise',
  auf_anfrage: 'auf Anfrage',
  unklar: 'unklar',
}

const STATUS_LABEL: Record<string, string> = {
  gesichtet: 'gesichtet',
  vorgemerkt: 'vorgemerkt',
  in_pipeline: 'in Pipeline',
  verworfen: 'verworfen',
}

/** Eine Chance auf einen Blick: Score, die vier Kennzahlen, die Signale und die
 *  drei Zeilen, die im Gespräch tragen (Nutzer, Pain, KI-Idee). */
export default function ProductCard({
  p,
  rank,
  onOpen,
}: {
  p: MarketProduct
  rank?: number
  onOpen: (p: MarketProduct) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(p)}
      className="card p-4 text-left w-full flex flex-col gap-3 hover:border-outline transition-colors relative"
    >
      {rank != null && (
        <span className="absolute top-3 right-4 text-[11px] text-text-muted tabular-nums">#{rank}</span>
      )}

      <div className="pr-6">
        <h3 className="text-sm font-medium text-text leading-tight">{p.produkt}</h3>
        <p className="text-xs text-text-muted mt-0.5">{p.vendor} · {p.kategorie}</p>
      </div>

      <div className="flex items-center gap-2.5">
        <span className="text-xl font-semibold text-text tabular-nums w-9">{p.score}</span>
        <span className="flex-1 h-1.5 rounded-full bg-surface-high overflow-hidden">
          <span className="block h-full bg-md-primary rounded-full" style={{ width: `${p.score}%` }} />
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {[
          [p.lead, 'Lead'],
          [p.business, 'Business'],
          [p.refs, 'Referenzen'],
          [p.prio, 'Priorität'],
        ].map(([v, l]) => (
          <div key={String(l)} className="rounded-sm bg-surface-low px-2 py-1.5">
            <div className="text-sm font-semibold text-text tabular-nums">{v}</div>
            <div className="text-[10px] text-text-muted">{l}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-1 text-[10.5px]">
        <span className="px-1.5 py-0.5 rounded-full bg-md-primary-container text-on-primary-container">Prio {p.prio}</span>
        <span className="px-1.5 py-0.5 rounded-full border border-outline-variant text-text-muted">
          Integration {p.int_level}
        </span>
        {p.marketplace && (
          <span className="px-1.5 py-0.5 rounded-full border border-success/40 text-success">⬡ Marktplatz</span>
        )}
        {p.reg.length > 0 && (
          <span className="px-1.5 py-0.5 rounded-full border border-warning/40 text-warning">
            § {p.reg[0]}{p.reg.length > 1 ? ` +${p.reg.length - 1}` : ''}
          </span>
        )}
        {p.self_compete && (
          <span className="px-1.5 py-0.5 rounded-full border border-danger/50 text-danger inline-flex items-center gap-1">
            <Icon name="warning" size={11} /> Wettbewerb
          </span>
        )}
        <span className="px-1.5 py-0.5 rounded-full border border-outline-variant text-text-muted">
          Verzeichnis {REF_LABEL[p.ref_status]}
        </span>
        {p.status !== 'neu' && (
          <span className="px-1.5 py-0.5 rounded-full bg-surface-high text-text">{STATUS_LABEL[p.status]}</span>
        )}
      </div>

      <dl className="border-t border-outline-variant pt-2.5 space-y-1.5 text-xs">
        {[
          ['Nutzer', p.nutzer[0]],
          ['Pain', p.pains[0]],
          ['KI-Idee', p.ki[0]],
          ['Nutzen', p.nutzen],
        ].map(([k, v]) =>
          v ? (
            <div key={k as string} className="grid grid-cols-[62px_1fr] gap-2">
              <dt className="text-text-muted text-[11px]">{k}</dt>
              <dd className={k === 'KI-Idee' ? 'text-text' : 'text-text-muted'}>{v}</dd>
            </div>
          ) : null,
        )}
      </dl>
    </button>
  )
}
