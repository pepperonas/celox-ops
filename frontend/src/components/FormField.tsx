interface SelectOption {
  value: string | number
  label: string
}

interface FormFieldProps {
  label: string
  name: string
  type?: 'text' | 'email' | 'tel' | 'number' | 'date' | 'textarea' | 'select' | 'checkbox'
  value: string | number | boolean
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  error?: string | null
  required?: boolean
  options?: SelectOption[]
  placeholder?: string
  disabled?: boolean
  step?: string
  min?: string | number
}

export default function FormField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  error,
  required,
  options,
  placeholder,
  disabled,
  step,
  min,
}: FormFieldProps) {
  const id = `field-${name}`

  if (type === 'checkbox') {
    return (
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id={id}
          name={name}
          checked={value as boolean}
          onChange={onChange}
          disabled={disabled}
          className="w-4 h-4 rounded-[6px] border-border bg-surface text-accent focus:ring-accent focus:ring-offset-bg"
        />
        <label htmlFor={id} className="text-xs uppercase tracking-wider text-text-muted">
          {label}
          {required && <span className="text-danger ml-1">*</span>}
        </label>
        {error && <p className="text-xs text-danger mt-1">{error}</p>}
      </div>
    )
  }

  return (
    <div>
      <label htmlFor={id} className="block text-xs uppercase tracking-wider text-text-muted mb-2">
        {label}
        {required && <span className="text-danger ml-1">*</span>}
      </label>

      {type === 'select' ? (
        <select
          id={id}
          name={name}
          value={value as string | number}
          onChange={onChange}
          disabled={disabled}
          className="w-full"
        >
          <option value="">{placeholder || 'Bitte wählen...'}</option>
          {options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : type === 'textarea' ? (
        <textarea
          id={id}
          name={name}
          value={value as string}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          rows={4}
          className="input-field resize-y"
        />
      ) : (
        <input
          type={type}
          id={id}
          name={name}
          value={value as string | number}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          step={step}
          min={min}
          className="w-full"
        />
      )}

      {error && <p className="text-xs text-danger mt-1">{error}</p>}
    </div>
  )
}
