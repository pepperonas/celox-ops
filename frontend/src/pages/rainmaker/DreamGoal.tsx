import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import LoadingIndicator from '../../components/LoadingIndicator'
import RainmakerNav from './RainmakerNav'
import RainmakerFooter from './RainmakerFooter'
import { getRainmakerDream, updateRainmakerSettings } from '../../api/rainmaker'
import { formatCurrency, formatDate } from '../../utils/formatters'
import type { RainmakerDreamMode, RainmakerDreamResponse } from '../../types'
import {
  DREAM_PRESETS, DREAM_MILESTONES, presetByKey,
  euroToKm, monthsEarlier,
} from './dreamPresets'

// Normalized (Number()-coerced) view of the API response.
interface Dream {
  goalKey: string | null
  goalName: string
  price: number
  ratePct: number
  avgDeal: number
  contactsPerWin: number
  startDate: string
  mode: RainmakerDreamMode
  evUnit: number
  weights: Record<string, number>
  activitiesEv: number
  wonCount: number
  wonEv: number
  invoicesPaid: number
  invoicesEv: number
  saved: number
  pct: number
  todayEv: number
  pacePerDay: number
  projectedDate: string | null
  daysActive: number
}

function normalize(d: RainmakerDreamResponse): Dream {
  return {
    goalKey: d.goal_key,
    goalName: d.goal_name,
    price: Number(d.goal_price),
    ratePct: Number(d.savings_rate_pct),
    avgDeal: Number(d.avg_deal_value),
    contactsPerWin: Number(d.contacts_per_win),
    startDate: d.start_date,
    mode: d.mode,
    evUnit: Number(d.ev_per_contact),
    weights: d.ev_weights,
    activitiesEv: Number(d.activities_ev),
    wonCount: d.won_count,
    wonEv: Number(d.won_ev),
    invoicesPaid: Number(d.invoices_paid),
    invoicesEv: Number(d.invoices_ev),
    saved: Number(d.saved_total),
    pct: Number(d.pct),
    todayEv: Number(d.today_ev),
    pacePerDay: Number(d.pace_per_day),
    projectedDate: d.projected_date,
    daysActive: d.days_active,
  }
}

const fmtKm = (km: number) =>
  km >= 100 ? Math.round(km).toLocaleString('de-DE') : km.toLocaleString('de-DE', { maximumFractionDigits: 1 })

// --------------------------------------------------------------------------
// Randomized scenario cards — "was passiert, wenn …"
// --------------------------------------------------------------------------
interface Scenario { icon: string; title: string; gain: number; note: string }

function buildScenarios(d: Dream): Scenario[] {
  const rate = d.ratePct / 100
  const pick = <T,>(arr: T[]) => arr[Math.floor(Math.random() * arr.length)]
  const calls = pick([3, 5, 8, 10])
  const deal = pick([8000, 15000, 25000, 40000])
  const mails = pick([5, 10, 15])
  const weeks = pick([1, 2])
  const wVisit = d.weights['visit'] ?? 2.5
  const wEmail = d.weights['email'] ?? 0.4
  const wFollow = d.weights['follow_up'] ?? 0.8

  const pool: Scenario[] = [
    {
      icon: '📞', title: `${calls} Anrufe heute`, gain: calls * d.evUnit,
      note: 'Auch wenn alle Nein sagen — die Statistik zahlt trotzdem aufs Auto ein.',
    },
    {
      icon: '❌', title: 'Ein Nein am Telefon', gain: d.evUnit,
      note: `Bei ${d.contactsPerWin} Kontakten pro Abschluss ist jedes Nein ein bezahlter Schritt zum nächsten Ja.`,
    },
    {
      icon: '🤝', title: 'Ein Vor-Ort-Termin', gain: wVisit * d.evUnit,
      note: `Zählt ${wVisit}× so viel wie ein Anruf — Präsenz schlägt Pixel.`,
    },
    {
      icon: '🏆', title: `Ein Abschluss à ${formatCurrency(deal)}`, gain: deal * rate,
      note: `${formatCurrency(deal * rate)} in den Traum-Topf = ${fmtKm(euroToKm(deal * rate))} km Fahrstrecke.`,
    },
    {
      icon: '📬', title: `${mails} Akquise-Mails raus`, gain: mails * wEmail * d.evUnit,
      note: 'Der leise Weg: weniger wert pro Stück, aber skalierbar.',
    },
    {
      icon: '🔁', title: 'Ein konsequentes Follow-up', gain: wFollow * d.evUnit,
      note: 'Die meisten Deals sterben am Nicht-Nachfassen, nicht am Nein.',
    },
    {
      icon: '🔥', title: `${weeks === 1 ? 'Eine Woche' : 'Zwei Wochen'} lang 5 Anrufe/Tag`, gain: weeks * 5 * 5 * d.evUnit,
      note: `${weeks * 25} Kontakte — statistisch ${(weeks * 25 / d.contactsPerWin).toLocaleString('de-DE', { maximumFractionDigits: 1 })} neue Kunden.`,
    },
    {
      icon: '🚀', title: `Retainer-Kunde à ${formatCurrency(3000)}/Monat, 12 Monate`, gain: 36000 * rate,
      note: `Ein einziger Dauerkunde = ${fmtKm(euroToKm(36000 * rate))} km Richtung Ziel.`,
    },
  ]
  // Shuffle, keep 4.
  return pool.map((s) => ({ s, r: Math.random() })).sort((a, b) => a.r - b.r).slice(0, 4).map((x) => x.s)
}

const QUOTES = [
  (g: string) => `Der ${g} wartet nicht auf Motivation. Er wartet auf Anrufe.`,
  (g: string) => `Jeder Anruf ist Tanken. Jedes Nein ist trotzdem Strecke.`,
  (g: string) => `Du kaufst den ${g} nicht beim Händler. Du kaufst ihn am Telefon.`,
  (g: string) => `Heute 5 Kontakte sind morgen ein Kunde und übermorgen ein Schlüssel.`,
  (g: string) => `Verkäufer zählen Abschlüsse. Champions zählen Versuche.`,
]

export default function RainmakerDreamGoal() {
  const [dream, setDream] = useState<Dream | null>(null)
  const [loading, setLoading] = useState(true)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [quoteIdx, setQuoteIdx] = useState(0)
  const [showConfig, setShowConfig] = useState(false)
  const [saving, setSaving] = useState(false)

  // What-if calculator state.
  const [whatIfValue, setWhatIfValue] = useState(15000)
  const [whatIfCount, setWhatIfCount] = useState(1)

  // Config draft.
  const [cfg, setCfg] = useState({
    key: 'cayenne_turbo_e', name: '', price: 165500,
    ratePct: 30, avgDeal: 15000, contactsPerWin: 20, startDate: '', mode: 'ev' as RainmakerDreamMode,
  })

  const load = useCallback(async () => {
    try {
      const d = normalize(await getRainmakerDream())
      setDream(d)
      setScenarios(buildScenarios(d))
      setQuoteIdx(Math.floor(Math.random() * QUOTES.length))
      setCfg({
        key: d.goalKey ?? 'cayenne_turbo_e', name: d.goalName, price: d.price,
        ratePct: d.ratePct, avgDeal: d.avgDeal, contactsPerWin: d.contactsPerWin,
        startDate: d.startDate, mode: d.mode,
      })
    } catch {
      toast.error('Traumziel konnte nicht geladen werden.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const preset = presetByKey(dream?.goalKey)
  const remaining = dream ? Math.max(dream.price - dream.saved, 0) : 0
  const callsLeft = dream && dream.evUnit > 0 ? Math.ceil(remaining / dream.evUnit) : null
  const pctDisplay = dream ? Math.min(dream.pct * 100, 100) : 0

  const whatIf = useMemo(() => {
    if (!dream) return null
    const gain = whatIfValue * whatIfCount * (dream.ratePct / 100)
    return { gain, km: euroToKm(gain), months: monthsEarlier(gain, dream.pacePerDay) }
  }, [dream, whatIfValue, whatIfCount])

  const saveConfig = async () => {
    setSaving(true)
    try {
      const p = DREAM_PRESETS.find((x) => x.key === cfg.key)
      await updateRainmakerSettings({
        dream_goal_key: cfg.key,
        dream_goal_name: cfg.key === 'custom' ? (cfg.name || 'Eigenes Ziel') : (p?.name ?? cfg.name),
        dream_goal_price: cfg.price,
        dream_savings_rate_pct: cfg.ratePct,
        dream_avg_deal_value: cfg.avgDeal,
        dream_contacts_per_win: cfg.contactsPerWin,
        dream_start_date: cfg.startDate || null,
        dream_mode: cfg.mode,
      })
      toast.success('Traumziel gespeichert.')
      setShowConfig(false)
      await load()
    } catch {
      toast.error('Speichern fehlgeschlagen.')
    }
    setSaving(false)
  }

  if (loading || !dream) {
    return (
      <div className="pb-4">
        <PageHeader title="Traumziel" subtitle="Dein Warum, in Euro und Kilometern" />
        <RainmakerNav />
        <LoadingIndicator />
      </div>
    )
  }

  const kmTotal = euroToKm(dream.price)
  const kmDone = euroToKm(dream.saved)

  return (
    <div className="pb-4">
      <PageHeader title="Traumziel" subtitle="Dein Warum, in Euro und Kilometern" />
      <RainmakerNav />

      {/* ---------- Hero: the car ---------- */}
      <div
        className="rounded-card overflow-hidden mb-6 shadow-elev-2 animate-md-enter"
        style={{ background: `linear-gradient(135deg, ${preset.colors[0]}, ${preset.colors[1]})` }}
      >
        <div className="p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
            <div className="text-6xl sm:text-7xl leading-none drop-shadow-lg select-none">{preset.emoji}</div>
            <div className="flex-1 min-w-0">
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{dream.goalName}</h2>
              <p className="text-white/70 text-sm mt-1">{preset.tagline}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                {preset.specs.map((s) => (
                  <span key={s} className="text-[11px] font-semibold px-3 py-1 rounded-full bg-white/15 text-white backdrop-blur-sm">{s}</span>
                ))}
                <span className="text-[11px] font-semibold px-3 py-1 rounded-full bg-white/25 text-white">{formatCurrency(dream.price)}</span>
              </div>
            </div>
            <div className="text-left sm:text-right shrink-0">
              <div className="text-3xl sm:text-4xl font-bold text-white tabular-nums">{pctDisplay.toLocaleString('de-DE', { maximumFractionDigits: 1 })}%</div>
              <div className="text-white/70 text-xs mt-0.5">{formatCurrency(dream.saved)} im Traum-Topf</div>
            </div>
          </div>

          {/* ---------- The road: 1.000 € = 1 km ---------- */}
          <div className="mt-7">
            <div className="relative h-16">
              {/* milestones */}
              {DREAM_MILESTONES.map((m) => {
                const reached = dream.pct >= m.at
                return (
                  <div key={m.at} className="absolute -translate-x-1/2 text-center" style={{ left: `${m.at * 100}%`, top: 0 }}>
                    <div className={`text-lg leading-none transition-all duration-long ${reached ? 'scale-110' : 'opacity-35 grayscale'}`}>{m.icon}</div>
                    <div className={`text-[9px] mt-0.5 whitespace-nowrap ${reached ? 'text-white' : 'text-white/40'} hidden sm:block`}>{m.label}</div>
                  </div>
                )
              })}
              {/* road */}
              <div className="absolute left-0 right-0 bottom-0 h-6 rounded-full bg-black/40 overflow-hidden">
                <div className="absolute inset-x-3 top-1/2 -translate-y-1/2 h-[2px]"
                  style={{ backgroundImage: 'repeating-linear-gradient(90deg, rgba(255,255,255,.55) 0 12px, transparent 12px 26px)' }} />
                {/* progress glow */}
                <div className="absolute left-0 top-0 bottom-0 rounded-full transition-all duration-long ease-emphasized"
                  style={{ width: `${pctDisplay}%`, background: 'linear-gradient(90deg, rgba(255,255,255,.08), rgba(255,255,255,.28))' }} />
              </div>
              {/* the car drives the road */}
              <div className="absolute bottom-0.5 -translate-x-1/2 text-xl transition-all duration-long ease-emphasized select-none"
                style={{ left: `calc(${Math.max(pctDisplay, 1.5)}% )` }}>
                <span className="inline-block -scale-x-100">{preset.emoji}</span>
              </div>
            </div>
            <div className="flex justify-between text-[11px] text-white/70 mt-2 tabular-nums">
              <span>km {fmtKm(kmDone)} von {fmtKm(kmTotal)}</span>
              <span>1.000 € = 1 km</span>
            </div>
          </div>
        </div>

        {/* stacked source bar */}
        <div className="bg-black/25 px-6 sm:px-8 py-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px] text-white/80">
          {dream.mode === 'ev' ? (
            <>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-sky-300 inline-block" /> Statistisch erarbeitet: <strong className="tabular-nums">{formatCurrency(dream.activitiesEv)}</strong></span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-300 inline-block" /> Realisiert ({dream.wonCount} Win{dream.wonCount !== 1 ? 's' : ''}): <strong className="tabular-nums">{formatCurrency(dream.wonEv)}</strong></span>
            </>
          ) : (
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-300 inline-block" /> Aus bezahlten Rechnungen ({formatCurrency(dream.invoicesPaid)} × {dream.ratePct} %): <strong className="tabular-nums">{formatCurrency(dream.invoicesEv)}</strong></span>
          )}
          <button onClick={() => setShowConfig((v) => !v)} className="ml-auto text-white/70 hover:text-white transition-colors">⚙️ Ziel & Annahmen</button>
        </div>
      </div>

      {/* ---------- Momentum stats ---------- */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6 md-stagger">
        <div className="card !py-4">
          <div className="text-xs text-text-muted">Heute erarbeitet</div>
          <div className={`text-xl font-bold tabular-nums mt-1 ${dream.todayEv > 0 ? 'text-success' : 'text-text'}`}>
            {dream.todayEv > 0 ? '+' : ''}{formatCurrency(dream.todayEv)}
          </div>
          <div className="text-[10px] text-text-muted mt-0.5">≈ {fmtKm(euroToKm(dream.todayEv))} km gefahren</div>
        </div>
        <div className="card !py-4">
          <div className="text-xs text-text-muted">Dein Tempo</div>
          <div className="text-xl font-bold tabular-nums mt-1 text-text">{formatCurrency(dream.pacePerDay * 7)}<span className="text-xs font-normal text-text-muted">/Woche</span></div>
          <div className="text-[10px] text-text-muted mt-0.5">Ø der letzten 28 Tage</div>
        </div>
        <div className="card !py-4">
          <div className="text-xs text-text-muted">Schlüsselübergabe</div>
          <div className="text-xl font-bold tabular-nums mt-1 text-text">
            {dream.projectedDate ? formatDate(dream.projectedDate) : '—'}
          </div>
          <div className="text-[10px] text-text-muted mt-0.5">{dream.projectedDate ? 'bei aktuellem Tempo' : 'Tempo aufnehmen → Datum erscheint'}</div>
        </div>
        <div className="card !py-4">
          <div className="text-xs text-text-muted">Noch nötig</div>
          <div className="text-xl font-bold tabular-nums mt-1 text-accent">{callsLeft != null ? `≈ ${callsLeft.toLocaleString('de-DE')} Anrufe` : '—'}</div>
          <div className="text-[10px] text-text-muted mt-0.5">{formatCurrency(remaining)} offen · Tag {dream.daysActive} der Challenge</div>
        </div>
      </div>

      {/* ---------- Scenario cards ---------- */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text">Was bringt dich weiter — jetzt gerade?</h3>
        <button
          onClick={() => { setScenarios(buildScenarios(dream)); setQuoteIdx((quoteIdx + 1) % QUOTES.length) }}
          className="md-state text-xs text-text-muted hover:text-text px-3 py-1.5 rounded-full"
          title="Neue Konstellationen würfeln"
        >
          🎲 Neu mischen
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6 md-stagger">
        {scenarios.map((s, i) => (
          <div key={`${s.title}-${i}`} className="card !py-4 flex gap-3 items-start hover:shadow-elev-2 transition-shadow duration-medium">
            <div className="text-2xl leading-none select-none">{s.icon}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="text-sm font-medium text-text">{s.title}</span>
                <span className="text-sm font-bold text-success tabular-nums shrink-0">+{formatCurrency(s.gain)}</span>
              </div>
              <p className="text-xs text-text-muted mt-1">{s.note}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ---------- What-if calculator ---------- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold text-text mb-4">Was-wäre-wenn-Rechner</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-text-muted">Auftragswert pro Kunde</span>
              <span className="text-text font-semibold tabular-nums">{formatCurrency(whatIfValue)}</span>
            </div>
            <input type="range" min={1000} max={100000} step={1000} value={whatIfValue}
              onChange={(e) => setWhatIfValue(Number(e.target.value))} className="w-full" />
            <div className="flex justify-between text-xs mt-3 mb-2">
              <span className="text-text-muted">Anzahl gewonnener Kunden</span>
              <span className="text-text font-semibold tabular-nums">{whatIfCount}</span>
            </div>
            <input type="range" min={1} max={10} step={1} value={whatIfCount}
              onChange={(e) => setWhatIfCount(Number(e.target.value))} className="w-full" />
          </div>
          {whatIf && (
            <div className="rounded-lg bg-surface-high p-4 flex flex-col justify-center">
              <p className="text-sm text-text">
                Gewinnst du <strong>{whatIfCount} Kunde{whatIfCount !== 1 ? 'n' : ''}</strong> à <strong>{formatCurrency(whatIfValue)}</strong>, wandern bei {dream.ratePct} % Sparquote
              </p>
              <p className="text-2xl font-bold text-success tabular-nums my-2">+{formatCurrency(whatIf.gain)}</p>
              <p className="text-xs text-text-muted">
                in den Traum-Topf — das sind <strong className="text-text">{fmtKm(whatIf.km)} km</strong> Strecke
                {whatIf.months != null && whatIf.months >= 0.05 && (
                  <> und die Schlüsselübergabe rückt <strong className="text-text">{whatIf.months >= 1 ? `${whatIf.months.toLocaleString('de-DE', { maximumFractionDigits: 1 })} Monate` : `${Math.round(whatIf.months * 30.44)} Tage`}</strong> näher</>
                )}.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ---------- Config ---------- */}
      {showConfig && (
        <div className="card mb-6 animate-md-enter">
          <h3 className="text-sm font-semibold text-text mb-4">Ziel & Annahmen</h3>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
            {DREAM_PRESETS.map((p) => (
              <button key={p.key} type="button"
                onClick={() => setCfg({ ...cfg, key: p.key, price: p.key === cfg.key ? cfg.price : p.price, name: p.key === 'custom' ? cfg.name : p.name })}
                className={`text-left rounded-lg p-3 border transition-all duration-short ${cfg.key === p.key ? 'border-accent bg-accent/10' : 'border-border bg-surface-high hover:border-text-muted'}`}>
                <div className="text-2xl leading-none mb-1.5">{p.emoji}</div>
                <div className="text-xs font-medium text-text leading-tight">{p.name}</div>
                <div className="text-[10px] text-text-muted mt-0.5 tabular-nums">{formatCurrency(p.price)}</div>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {cfg.key === 'custom' && (
              <div>
                <label className="block text-xs text-text-muted mb-2">Name deines Ziels</label>
                <input type="text" value={cfg.name} onChange={(e) => setCfg({ ...cfg, name: e.target.value })} className="w-full" placeholder="z. B. Finca auf Mallorca" />
              </div>
            )}
            <div>
              <label className="block text-xs text-text-muted mb-2">Zielpreis (€)</label>
              <input type="number" min={1000} step={500} value={cfg.price} onChange={(e) => setCfg({ ...cfg, price: Number(e.target.value) })} className="w-full" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-2">Start der Challenge</label>
              <input type="date" value={cfg.startDate} onChange={(e) => setCfg({ ...cfg, startDate: e.target.value })} className="w-full" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-text-muted">Sparquote (vom Netto-Umsatz)</span>
                <span className="text-text font-semibold tabular-nums">{cfg.ratePct} %</span>
              </div>
              <input type="range" min={5} max={100} step={5} value={cfg.ratePct} onChange={(e) => setCfg({ ...cfg, ratePct: Number(e.target.value) })} className="w-full" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-2">Ø Auftragswert (€)</label>
              <input type="number" min={500} step={500} value={cfg.avgDeal} onChange={(e) => setCfg({ ...cfg, avgDeal: Number(e.target.value) })} className="w-full" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-2">Kontakte pro Abschluss</label>
              <input type="number" min={1} max={200} value={cfg.contactsPerWin} onChange={(e) => setCfg({ ...cfg, contactsPerWin: Number(e.target.value) })} className="w-full" />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 mb-2">
            <div className="flex gap-1 p-1 rounded-full bg-surface-container w-fit">
              <button type="button" onClick={() => setCfg({ ...cfg, mode: 'ev' })}
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-short ${cfg.mode === 'ev' ? 'bg-md-primary text-on-primary' : 'text-text-muted'}`}>
                Erwartungswert (Aktionen)
              </button>
              <button type="button" onClick={() => setCfg({ ...cfg, mode: 'invoices' })}
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-short ${cfg.mode === 'invoices' ? 'bg-md-primary text-on-primary' : 'text-text-muted'}`}>
                Echte Rechnungen
              </button>
            </div>
            <p className="text-[11px] text-text-muted flex-1 min-w-[200px]">
              Erwartungswert: jede Aktion zählt statistisch ({formatCurrency(evLive(cfg))} pro Anruf). Rechnungen: nur bezahlter Umsatz × Sparquote — für später, wenn das Business läuft.
            </p>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button onClick={() => setShowConfig(false)} className="btn-secondary" disabled={saving}>Abbrechen</button>
            <button onClick={saveConfig} className="btn-primary" disabled={saving}>{saving ? 'Speichern…' : 'Speichern'}</button>
          </div>
        </div>
      )}

      {/* ---------- Quote ---------- */}
      <p className="text-center text-sm text-text-muted italic mt-8 mb-2">„{QUOTES[quoteIdx](dream.goalName)}"</p>

      <RainmakerFooter />
    </div>
  )
}

function evLive(cfg: { avgDeal: number; ratePct: number; contactsPerWin: number }): number {
  return (cfg.avgDeal * (cfg.ratePct / 100)) / Math.max(cfg.contactsPerWin, 1)
}
