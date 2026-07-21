import Select, { type SelectChangeEvent } from './Select'

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
          style={{ accentColor: 'var(--md-primary)' }}
          className="w-[18px] h-[18px] rounded cursor-pointer"
        />
        <label htmlFor={id} className="text-xs text-text-muted">
          {label}
          {required && <span className="text-danger ml-1">*</span>}
        </label>
        {error && <p className="text-xs text-danger mt-1">{error}</p>}
      </div>
    )
  }

  return (
    <div>
      <label htmlFor={id} className="block text-xs text-text-muted mb-2">
        {label}
        {required && <span className="text-danger ml-1">*</span>}
      </label>

      {type === 'select' ? (
        // App-eigenes Dropdown statt nativem <select>. Der Cast ist bewusst und
        // hier gekapselt: Select liefert ein {target:{name,value}}-Event, damit
        // die bestehenden ChangeEvent-Handler unverändert weiterlaufen.
        <Select
          id={id}
          name={name}
          value={value as string | number}
          onChange={onChange as unknown as (e: SelectChangeEvent) => void}
          options={options ?? []}
          placeholder={placeholder || 'Bitte wählen...'}
          disabled={disabled}
          required={required}
        />
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
