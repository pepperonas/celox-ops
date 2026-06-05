// MD3 tonal chip styles — container tint + on-container text, pill shaped.
const tones = {
  accent: 'bg-accent/15 text-accent',
  success: 'bg-success/15 text-success',
  warning: 'bg-warning/20 text-warning',
  danger: 'bg-danger/15 text-danger',
  purple: 'bg-purple/15 text-purple',
  cyan: 'bg-cyan/15 text-cyan',
  neutral: 'bg-surface-high text-text-muted',
} as const

const statusColors: Record<string, string> = {
  // Order statuses
  angebot: tones.warning,
  beauftragt: tones.accent,
  in_arbeit: tones.purple,
  abgeschlossen: tones.success,
  storniert: tones.danger,
  // Contract statuses
  aktiv: tones.success,
  gekuendigt: tones.warning,
  ausgelaufen: tones.danger,
  // Invoice statuses
  entwurf: tones.neutral,
  gestellt: tones.accent,
  bezahlt: tones.success,
  ueberfaellig: tones.danger,
  // Lead statuses
  neu: tones.warning,
  kontaktiert: tones.accent,
  interessiert: tones.purple,
  abgelehnt: tones.danger,
  // Contract types
  hosting: tones.accent,
  wartung: tones.purple,
  support: tones.success,
  sonstige: tones.neutral,
  // Billing cycles
  monatlich: tones.neutral,
  quartalsweise: tones.neutral,
  halbjaehrlich: tones.neutral,
  jaehrlich: tones.neutral,
  // Expense categories
  domain: tones.accent,
  software: tones.purple,
  lizenz: tones.purple,
  hardware: tones.warning,
  ki_api: tones.cyan,
  werbung: tones.success,
  buero: tones.neutral,
  reise: tones.warning,
}

const statusLabels: Record<string, string> = {
  angebot: 'Angebot',
  beauftragt: 'Beauftragt',
  in_arbeit: 'In Arbeit',
  abgeschlossen: 'Abgeschlossen',
  storniert: 'Storniert',
  aktiv: 'Aktiv',
  gekuendigt: 'Gekündigt',
  ausgelaufen: 'Ausgelaufen',
  entwurf: 'Entwurf',
  gestellt: 'Gestellt',
  bezahlt: 'Bezahlt',
  ueberfaellig: 'Überfällig',
  neu: 'Neu',
  kontaktiert: 'Kontaktiert',
  interessiert: 'Interessiert',
  abgelehnt: 'Abgelehnt',
  hosting: 'Hosting',
  wartung: 'Wartung',
  support: 'Support',
  sonstige: 'Sonstige',
  // Billing cycles
  monatlich: 'Monatlich',
  quartalsweise: 'Quartalsweise',
  halbjaehrlich: 'Halbjährlich',
  jaehrlich: 'Jährlich',
  // Expense categories
  domain: 'Domain',
  software: 'Software',
  lizenz: 'Lizenz',
  hardware: 'Hardware',
  ki_api: 'KI/API',
  werbung: 'Werbung',
  buero: 'Büro',
  reise: 'Reise',
}

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = statusColors[status] || tones.neutral
  const label = statusLabels[status] || status

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium transition-colors duration-short ${colorClass}`}
    >
      {label}
    </span>
  )
}
