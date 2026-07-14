import type { TimeField, TimePreset } from './timeFilter'

export interface TimeFilterValue {
  field: TimeField
  preset: TimePreset
  from: string        // datetime-local (lokal)
  to: string
}

export const DEFAULT_TIME_FILTER: TimeFilterValue = {
  field: 'created', preset: 'all', from: '', to: '',
}

const PRESETS: { key: TimePreset; label: string }[] = [
  { key: 'all', label: 'Alle' },
  { key: '15m', label: '15 Min' },
  { key: '1h', label: '1 Std' },
  { key: 'today', label: 'Heute' },
  { key: '24h', label: '24 Std' },
  { key: '7d', label: '7 Tage' },
  { key: 'lastImport', label: '✦ Letzter Import' },
  { key: 'custom', label: 'Eigen…' },
]

function chipCls(active: boolean): string {
  return `text-xs px-3 py-1 rounded-full border transition-colors duration-short ${
    active ? 'border-accent bg-accent/15 text-text' : 'border-border text-text-muted hover:text-text'
  }`
}

export default function PipelineTimeFilter({
  value, onChange, matchCount, totalCount,
}: {
  value: TimeFilterValue
  onChange: (patch: Partial<TimeFilterValue>) => void
  matchCount: number
  totalCount: number
}) {
  const active = value.preset !== 'all'
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-xs text-text-muted mr-1">Zeit:</span>

      {/* Feld-Umschalter Erstellt / Geändert */}
      <div className="inline-flex rounded-full border border-border overflow-hidden mr-1">
        {(['created', 'updated'] as const).map((f) => (
          <button
            key={f}
            onClick={() => onChange({ field: f })}
            className={`text-xs px-2.5 py-1 transition-colors duration-short ${
              value.field === f ? 'bg-accent/15 text-text' : 'text-text-muted hover:text-text'
            }`}
          >
            {f === 'created' ? 'Erstellt' : 'Geändert'}
          </button>
        ))}
      </div>

      {PRESETS.map(({ key, label }) => (
        <button key={key} onClick={() => onChange({ preset: key })} className={chipCls(value.preset === key)}>
          {label}
        </button>
      ))}

      {value.preset === 'custom' && (
        <div className="flex flex-wrap items-center gap-1.5">
          <input
            type="datetime-local" value={value.from}
            onChange={(e) => onChange({ from: e.target.value })}
            className="text-xs bg-surface-container border border-border rounded-lg px-2 py-1 text-text"
            aria-label="Von"
          />
          <span className="text-xs text-text-muted">–</span>
          <input
            type="datetime-local" value={value.to}
            onChange={(e) => onChange({ to: e.target.value })}
            className="text-xs bg-surface-container border border-border rounded-lg px-2 py-1 text-text"
            aria-label="Bis"
          />
        </div>
      )}

      {active && (
        <span className="text-xs text-text-muted ml-1">
          {matchCount} von {totalCount}
        </span>
      )}
    </div>
  )
}
