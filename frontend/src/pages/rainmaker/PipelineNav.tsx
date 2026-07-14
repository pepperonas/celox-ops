import { NavLink } from 'react-router-dom'

const items = [
  { to: '/pipeline', label: 'Pipeline', end: true },
  { to: '/pipeline/duplikate', label: 'Duplikate', end: false },
]

/** MD3 pill sub-navigation für die Pipeline (Akquise). */
export default function PipelineNav() {
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
          {item.label}
        </NavLink>
      ))}
    </div>
  )
}
