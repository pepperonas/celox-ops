interface Segment<T extends string> {
  value: T
  label: string
}

interface SegmentedButtonsProps<T extends string> {
  options: Segment<T>[]
  value: T
  onChange: (value: T) => void
  /** Smaller density for inline use (e.g. chart toggles). */
  dense?: boolean
}

const check = (
  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
  </svg>
)

/**
 * MD3 segmented buttons — connected pill group, single-select. Selected segment
 * fills with secondary-container and shows a leading check (MD3 convention).
 */
export default function SegmentedButtons<T extends string>({
  options,
  value,
  onChange,
  dense,
}: SegmentedButtonsProps<T>) {
  return (
    <div className="inline-flex p-1 rounded-full bg-surface-high">
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`md-state inline-flex items-center gap-1.5 rounded-full font-medium transition-all duration-short ease-spring ${
              dense ? 'px-3 py-1 text-[11px]' : 'px-4 py-1.5 text-xs'
            } ${
              active
                ? 'bg-md-secondary-container text-on-secondary-container'
                : 'text-text-muted hover:text-text'
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
