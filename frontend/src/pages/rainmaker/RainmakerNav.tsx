import { NavLink } from 'react-router-dom'
import Icon from '../../components/Icon'

const items = [
  { to: '/rainmaker', label: 'Heute', end: true },
  { to: '/rainmaker/traumziel', label: 'Traumziel', icon: 'finishFlag' as const, end: false },
  { to: '/rainmaker/statistik', label: 'Statistik', end: false },
  { to: '/rainmaker/einstellungen', label: 'Einstellungen', end: false },
]

/** MD3 pill sub-navigation shared across all Rainmaker screens. */
export default function RainmakerNav() {
  return (
    <div className="flex gap-1 mb-5 p-1 rounded-full bg-surface-high w-fit">
      {items.map((item) => (
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
          {item.icon && <Icon name={item.icon} size={16} className="mr-1.5 -mt-0.5" />}
          {item.label}
        </NavLink>
      ))}
    </div>
  )
}
