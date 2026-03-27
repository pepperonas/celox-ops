const statusColors: Record<string, string> = {
  // Order statuses
  angebot: 'bg-[#d2992233] text-warning border border-[#d2992240]',
  beauftragt: 'bg-[#58a6ff1a] text-accent border border-[#58a6ff30]',
  in_arbeit: 'bg-[#bc8cff1a] text-purple border border-[#bc8cff30]',
  abgeschlossen: 'bg-[#3fb95033] text-success border border-[#3fb95040]',
  storniert: 'bg-[#f8514933] text-danger border border-[#f8514940]',
  // Contract statuses
  aktiv: 'bg-[#3fb95033] text-success border border-[#3fb95040]',
  gekuendigt: 'bg-[#d2992233] text-warning border border-[#d2992240]',
  ausgelaufen: 'bg-[#f8514933] text-danger border border-[#f8514940]',
  // Invoice statuses
  entwurf: 'bg-surface-2 text-text-muted border border-border',
  gestellt: 'bg-[#58a6ff1a] text-accent border border-[#58a6ff30]',
  bezahlt: 'bg-[#3fb95033] text-success border border-[#3fb95040]',
  ueberfaellig: 'bg-[#f8514933] text-danger border border-[#f8514940]',
  // Lead statuses
  neu: 'bg-[#d2992233] text-warning border border-[#d2992240]',
  kontaktiert: 'bg-[#58a6ff1a] text-accent border border-[#58a6ff30]',
  interessiert: 'bg-[#bc8cff1a] text-purple border border-[#bc8cff30]',
  abgelehnt: 'bg-[#f8514933] text-danger border border-[#f8514940]',
  // Contract types
  hosting: 'bg-[#58a6ff1a] text-accent border border-[#58a6ff30]',
  wartung: 'bg-[#bc8cff1a] text-purple border border-[#bc8cff30]',
  support: 'bg-[#3fb95033] text-success border border-[#3fb95040]',
  sonstige: 'bg-surface-2 text-text-muted border border-border',
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
}

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = statusColors[status] || 'bg-surface-2 text-text-muted border border-border'
  const label = statusLabels[status] || status

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  )
}
