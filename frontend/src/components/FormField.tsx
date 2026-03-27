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
          className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-celox-500 focus:ring-celox-500 focus:ring-offset-gray-900"
        />
        <label htmlFor={id} className="text-sm font-medium text-gray-300">
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>
    )
  }

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-1.5">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>

      {type === 'select' ? (
        <select
          id={id}
          name={name}
          value={value as string | number}
          onChange={onChange}
          disabled={disabled}
          className="input-field"
        >
          <option value="">{placeholder || 'Bitte waehlen...'}</option>
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
          className="input-field"
        />
      )}

      {error && <p className="text-red-400 text-xs mt-1.5">{error}</p>}
    </div>
  )
}
