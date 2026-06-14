import type { RainmakerProgress } from '../../types'

interface Props {
  progress: RainmakerProgress
}

/** MD3 progress ring (Pensum) + streak + points header for the "Heute" view. */
export default function ProgressHeader({ progress }: Props) {
  const { daily_quota, done_today, current_streak, longest_streak, total_points } = progress
  const pct = daily_quota > 0 ? Math.min(done_today / daily_quota, 1) : 0
  const met = done_today >= daily_quota

  const r = 30
  const circ = 2 * Math.PI * r
  const dash = circ * pct

  return (
    <div className="card flex items-center gap-6 mb-6 animate-md-enter">
      {/* Pensum ring */}
      <div className="relative shrink-0" style={{ width: 76, height: 76 }}>
        <svg width="76" height="76" viewBox="0 0 76 76" className="-rotate-90">
          <circle cx="38" cy="38" r={r} fill="none" stroke="var(--md-surface-container-highest)" strokeWidth="7" />
          <circle
            cx="38" cy="38" r={r} fill="none"
            stroke={met ? 'var(--md-success)' : 'var(--md-primary)'}
            strokeWidth="7" strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            style={{ transition: 'stroke-dasharray 0.5s var(--md-ease-emphasized)' }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <span className="text-sm font-bold text-text tabular-nums">{done_today}/{daily_quota}</span>
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text">
          {met ? 'Tagespensum geschafft 🎉' : `Noch ${daily_quota - done_today} bis zum Pensum`}
        </p>
        <p className="text-xs text-text-muted mt-0.5">Akquise-Aktionen heute erledigt</p>
      </div>

      {/* Streak */}
      <div className="text-center shrink-0">
        <div className="text-2xl font-bold tabular-nums" style={{ color: current_streak > 0 ? '#e9c46a' : 'var(--text-muted)' }}>
          {current_streak > 0 ? `🔥${current_streak}` : '–'}
        </div>
        <div className="text-[10px] text-text-muted mt-0.5">Streak · längste {longest_streak}</div>
      </div>

      {/* Points */}
      <div className="text-center shrink-0">
        <div className="text-2xl font-bold tabular-nums text-accent">{total_points}</div>
        <div className="text-[10px] text-text-muted mt-0.5">Punkte</div>
      </div>
    </div>
  )
}
