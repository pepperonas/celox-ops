import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { canAdministerLeads } from '../../utils/permissions'

const items = [
  { to: '/pipeline', label: 'Pipeline', end: true, ownerOnly: false },
  { to: '/pipeline/duplikate', label: 'Duplikate', end: false, ownerOnly: true },
  // Aufsicht: nur für den Bereichs-Inhaber. Für einen Verkäufer wäre der
  // Papierkorb kein Sicherheitsnetz, sondern ein Zwischenschritt beim Löschen.
  { to: '/pipeline/papierkorb', label: 'Papierkorb', end: false, ownerOnly: true },
]

/** MD3 pill sub-navigation für die Pipeline (Akquise). */
export default function PipelineNav() {
  const role = useAuthStore((s) => s.role)
  const visible = items.filter((i) => !i.ownerOnly || canAdministerLeads(role))
  return (
    <div className="flex gap-1 mb-5 p-1 rounded-full bg-surface-high w-fit">
      {visible.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            `md-state px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-short ease-spring ${
              isActive
                ? 'bg-md-secondary-container text-on-secondary-container'
                : 'text-text-muted hover:text-text'
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  )
}
