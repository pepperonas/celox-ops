interface Props {
  checked: boolean
  onChange: (checked: boolean) => void
  /** Sichtbares Label rechts neben dem Schalter. */
  label?: string
  /** Erklärender Zusatz unter dem Label. */
  hint?: string
  disabled?: boolean
  'aria-label'?: string
}

/**
 * MD3-Schalter (Switch). Für An/Aus-Zustände, die sofort greifen — im Gegensatz
 * zur Checkbox, die eine Auswahl in einem Formular markiert.
 *
 * `role="switch"` + `aria-checked`; als <button> ist Leertaste/Enter nativ
 * bedienbar. Bewegung des Knopfes = Spatial-Token, Farbe = Effects-Token
 * (M3E-Kanon: Position darf federn, Farbe nie).
 */
export default function Toggle({ checked, onChange, label, hint, disabled, ...aria }: Props) {
  const button = (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      {...aria}
      className={`md-switch shrink-0 ${checked ? 'is-on' : ''}`}
    >
      <span className="md-switch-thumb" />
    </button>
  )

  if (!label && !hint) return button

  return (
    <label className={`flex items-start gap-3 ${disabled ? 'opacity-50' : 'cursor-pointer'}`}>
      {button}
      <span className="min-w-0">
        {label && <span className="block text-sm text-text">{label}</span>}
        {hint && <span className="block text-xs text-text-muted mt-0.5">{hint}</span>}
      </span>
    </label>
  )
}
