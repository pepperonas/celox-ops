interface ChipOption {
  value: string
  label: string
}

interface FilterChipsProps {
  options: ChipOption[]
  value: string
  onChange: (value: string) => void
}

const check = (
  <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
  </svg>
)

/**
 * MD3 filter chips — a wrapping row of selectable pills for single-select
 * filtering (e.g. status). The selected chip fills with secondary-container
 * and shows a leading check. Ideal for >5 options where segmented buttons
 * would be too wide.
 */
export default function FilterChips({ options, value, onChange }: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value || 'all'}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`md-state inline-flex items-center gap-1.5 px-4 h-8 rounded-lg text-xs font-medium transition-all duration-short ease-spring ${
              active
                ? 'bg-md-secondary-container text-on-secondary-container'
                : 'text-text-muted border border-border hover:text-text'
            }`}
          >
            {active && check}
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
