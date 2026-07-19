import { useEffect, useRef, useState } from 'react'
import type { RainmakerProgress } from '../../types'

interface Props {
  progress: RainmakerProgress
}

/** MD3 progress ring (Pensum) + streak + points header for the "Heute" view. */
export default function ProgressHeader({ progress }: Props) {
  const { daily_quota, done_today, current_streak, longest_streak, total_points, freeze_remaining } = progress
  const pct = daily_quota > 0 ? Math.min(done_today / daily_quota, 1) : 0
  const met = done_today >= daily_quota

  const r = 30
  const circ = 2 * Math.PI * r
  const dash = circ * pct

  // Pop the ring whenever the day's count climbs (the "Erledigt" payoff).
  const [pop, setPop] = useState(false)
  const prevDone = useRef(done_today)
  useEffect(() => {
    if (done_today > prevDone.current) {
      setPop(true)
      const t = setTimeout(() => setPop(false), 340)
      prevDone.current = done_today
      return () => clearTimeout(t)
    }
    prevDone.current = done_today
  }, [done_today])

  return (
    <div className="card flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 mb-6 animate-md-enter">
      {/* Ring + label */}
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className={`relative shrink-0 ${pop ? 'rm-ring-pop' : ''}`} style={{ width: 76, height: 76 }}>
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
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text">
            {met ? 'Tagespensum geschafft 🎉' : `Noch ${daily_quota - done_today} bis zum Pensum`}
          </p>
          <p className="text-xs text-text-muted mt-0.5">Akquise-Aktionen heute erledigt</p>
        </div>
      </div>

      {/* Streak + points (wrap to their own row on mobile) */}
      <div className="flex items-center gap-8 sm:gap-6 shrink-0">
        <div className="text-center">
          <div className="text-2xl md-title-emph tabular-nums leading-none" style={{ color: current_streak > 0 ? '#e9c46a' : 'var(--text-muted)' }}>
            {current_streak > 0 ? `🔥${current_streak}` : '–'}
          </div>
          <div className="text-[10px] text-text-muted mt-1 whitespace-nowrap" title="Streak zählt Werktage (Mo–Fr); Wochenenden brechen ihn nicht">
            Streak · längste {longest_streak}
          </div>
          <div className="text-[10px] text-text-muted mt-0.5 whitespace-nowrap" title="Freeze-Tage puffern verpasste Werktage">🧊 {freeze_remaining} Freeze{freeze_remaining !== 1 ? 's' : ''}</div>
        </div>
        <div className="text-center">
          <div className="text-2xl md-title-emph tabular-nums leading-none text-accent">{total_points}</div>
          <div className="text-[10px] text-text-muted mt-1">Punkte</div>
        </div>
      </div>
    </div>
  )
}
