const statusColors: Record<string, string> = {
  // Order statuses
  angebot: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  beauftragt: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  in_arbeit: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  abgeschlossen: 'bg-green-500/20 text-green-400 border-green-500/30',
  storniert: 'bg-red-500/20 text-red-400 border-red-500/30',
  // Contract statuses
  aktiv: 'bg-green-500/20 text-green-400 border-green-500/30',
  gekuendigt: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  ausgelaufen: 'bg-red-500/20 text-red-400 border-red-500/30',
  // Invoice statuses
  entwurf: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  gestellt: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  bezahlt: 'bg-green-500/20 text-green-400 border-green-500/30',
  ueberfaellig: 'bg-red-500/20 text-red-400 border-red-500/30',
  // Contract types
  hosting: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  wartung: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  support: 'bg-green-500/20 text-green-400 border-green-500/30',
  sonstige: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
}

const statusLabels: Record<string, string> = {
  angebot: 'Angebot',
  beauftragt: 'Beauftragt',
  in_arbeit: 'In Arbeit',
  abgeschlossen: 'Abgeschlossen',
  storniert: 'Storniert',
  aktiv: 'Aktiv',
  gekuendigt: 'Gekuendigt',
  ausgelaufen: 'Ausgelaufen',
  entwurf: 'Entwurf',
  gestellt: 'Gestellt',
  bezahlt: 'Bezahlt',
  ueberfaellig: 'Ueberfaellig',
  hosting: 'Hosting',
  wartung: 'Wartung',
  support: 'Support',
  sonstige: 'Sonstige',
}

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = statusColors[status] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  const label = statusLabels[status] || status

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}
    >
      {label}
    </span>
  )
}
