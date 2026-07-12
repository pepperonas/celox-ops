import type {
  RainmakerLeadStatus,
  RainmakerPriority,
  RainmakerActivityType,
  RainmakerOutcome,
} from '../../types'

export const STATUS_LABELS: Record<RainmakerLeadStatus, string> = {
  new: 'Neu',
  contacted: 'Kontaktiert',
  connected: 'Vernetzt',
  in_conversation: 'Im Gespräch',
  proposal: 'Angebot',
  won: 'Gewonnen',
  lost: 'Verloren',
  dormant: 'Ruhend',
}

export const STATUS_COLORS: Record<RainmakerLeadStatus, string> = {
  new: '#c9a227',
  contacted: '#7cb0ff',
  connected: '#57a6ff',
  in_conversation: '#a371f7',
  proposal: '#57dccb',
  won: '#74d98a',
  lost: '#ff6b62',
  dormant: '#9aa6b5',
}

// Pipeline column order (left → right).
export const PIPELINE_STATUSES: RainmakerLeadStatus[] = [
  'new',
  'contacted',
  'connected',
  'in_conversation',
  'proposal',
  'won',
  'lost',
  'dormant',
]

export const PRIORITY_LABELS: Record<RainmakerPriority, string> = {
  low: 'Niedrig',
  medium: 'Mittel',
  high: 'Hoch',
}

export const PRIORITY_TONE: Record<RainmakerPriority, string> = {
  low: 'bg-surface-high text-text-muted',
  medium: 'bg-accent/15 text-accent',
  high: 'bg-danger/15 text-danger',
}

export const ACTIVITY_TYPE_LABELS: Record<RainmakerActivityType, string> = {
  call: 'Anruf',
  email: 'E-Mail',
  visit: 'Besuch',
  message: 'Nachricht',
  follow_up: 'Nachfassen',
  note: 'Notiz',
}

export const ACTIVITY_TYPE_ICONS: Record<RainmakerActivityType, string> = {
  call: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
  email: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  visit: 'M17.657 16.657L13.414 20.9a2 2 0 01-2.828 0l-4.243-4.243a8 8 0 1111.314 0z',
  message: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4-.8L3 20l1.3-3.9A7.96 7.96 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  follow_up: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  note: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
}

export const OUTCOME_LABELS: Record<RainmakerOutcome, string> = {
  reached: 'Erreicht',
  no_answer: 'Nicht erreicht',
  positive: 'Positiv',
  negative: 'Negativ',
  meeting_set: 'Termin vereinbart',
  proposal_sent: 'Angebot raus',
  not_interested: 'Kein Interesse',
}
