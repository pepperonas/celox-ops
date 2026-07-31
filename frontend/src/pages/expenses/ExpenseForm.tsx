import { useAuthStore } from '../../store/authStore'
import { canDelete } from '../../utils/permissions'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import AutocompleteInput from '../../components/AutocompleteInput'
import Toggle from '../../components/Toggle'
import DeleteDialog from '../../components/DeleteDialog'
import FileAttachments from '../../components/FileAttachments'
import { getExpense, createExpense, updateExpense, deleteExpense } from '../../api/expenses'
import { getSuggestions } from '../../api/suggestions'
import type { ExpenseCategory, ExpenseCreate, ExpenseRecurrence } from '../../types'
import { useFormShortcuts } from '../../hooks/useFormShortcuts'
import { toastWithUndo } from '../../utils/undoToast'
import { formatCurrency } from '../../utils/formatters'
import {
  RECURRENCE_OPTIONS,
  monthlyEquivalent,
  yearlyEquivalent,
} from '../../utils/expenseRecurrence'
import { categoryFromDescriptionMap } from '../../utils/expensePayment'

const categoryOptions = [
  { value: 'hosting', label: 'Hosting' },
  { value: 'domain', label: 'Domain' },
  { value: 'software', label: 'Software' },
  { value: 'lizenz', label: 'Lizenz' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'ki_api', label: 'KI/API' },
  { value: 'werbung', label: 'Werbung' },
  { value: 'buero', label: 'Büro' },
  { value: 'reise', label: 'Reise' },
  { value: 'sonstige', label: 'Sonstige' },
]

const recurrenceSelectOptions = [
  { value: '', label: 'Einmalig' },
  ...RECURRENCE_OPTIONS.map((o) => ({ value: o.value, label: o.label })),
]

const today = () => new Date().toISOString().split('T')[0]

const emptyForm: ExpenseCreate = {
  description: '',
  category: 'sonstige',
  amount: 0,
  date: today(),
  vendor: '',
  recurring: false,
  recurrence: null,
  notes: '',
  paid: true,
  paid_at: today(),
}

export default function ExpenseForm() {
  const mayDelete = canDelete(useAuthStore((st) => st.role))
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<ExpenseCreate>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [categoryByDesc, setCategoryByDesc] = useState<Record<string, string>>({})

  useEffect(() => {
    getSuggestions('expense_description')
      .then((s) => setCategoryByDesc(s.categories || {}))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (id) {
      getExpense(id).then((e) =>
        setForm({
          description: e.description,
          category: e.category,
          amount: e.amount,
          date: e.date,
          vendor: e.vendor || '',
          recurring: e.recurring,
          recurrence: e.recurrence ?? (e.recurring ? 'monthly' : null),
          notes: e.notes || '',
          paid: e.paid,
          paid_at: e.paid_at,
          external_ref: e.external_ref,
        }),
      )
    }
  }, [id])

  const applyDescription = (description: string) => {
    const mapped = categoryFromDescriptionMap(description, categoryByDesc)
    setForm((prev) => ({
      ...prev,
      description,
      ...(mapped ? { category: mapped as ExpenseCategory } : {}),
    }))
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const target = e.target
    if (target.name === 'amount') {
      setForm({ ...form, amount: parseFloat(target.value) || 0 })
    } else if (target.name === 'recurrence') {
      const value = (target.value || null) as ExpenseRecurrence | null
      setForm({
        ...form,
        recurrence: value,
        recurring: value != null,
      })
    } else if (target.name === 'description') {
      applyDescription(target.value)
    } else if (target.name === 'date') {
      setForm({
        ...form,
        date: target.value,
        // Wenn bezahlt und Zahlungsdatum noch dem alten Buchungsdatum folgt → mitziehen.
        paid_at:
          form.paid && (form.paid_at === form.date || !form.paid_at)
            ? target.value
            : form.paid_at,
      })
    } else {
      setForm({ ...form, [target.name]: target.value })
    }
  }

  const setPaid = (paid: boolean) => {
    setForm({
      ...form,
      paid,
      paid_at: paid ? form.paid_at || form.date : null,
    })
  }

  const equiv = useMemo(() => {
    const monthly = monthlyEquivalent(Number(form.amount) || 0, form.recurrence ?? null)
    const yearly = yearlyEquivalent(Number(form.amount) || 0, form.recurrence ?? null)
    return { monthly, yearly }
  }, [form.amount, form.recurrence])

  useFormShortcuts({
    onSubmit: () => {
      if (loading) return
      const formEl = document.querySelector('form') as HTMLFormElement | null
      formEl?.requestSubmit()
    },
    onCancel: () => navigate(-1),
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload: ExpenseCreate = {
        ...form,
        recurrence: form.recurrence || null,
        recurring: Boolean(form.recurrence),
        paid: form.paid !== false,
        paid_at: form.paid === false ? null : form.paid_at || form.date,
      }
      if (isEdit) {
        await updateExpense(id!, payload)
        toast.success('Ausgabe aktualisiert.')
      } else {
        await createExpense(payload)
        toast.success('Ausgabe erstellt.')
      }
      navigate('/ausgaben')
    } catch {
      toast.error('Fehler beim Speichern.')
    }
    setLoading(false)
  }

  const handleDelete = async () => {
    if (!id) return
    const snapshot = { ...form }
    try {
      await deleteExpense(id)
      navigate('/ausgaben')
      toastWithUndo('Ausgabe gelöscht.', async () => {
        await createExpense(snapshot)
      })
    } catch {
      toast.error('Fehler beim Löschen.')
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-text tracking-tight">
          {isEdit ? 'Ausgabe bearbeiten' : 'Neue Ausgabe'}
        </h2>
        {isEdit && mayDelete && (
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Löschen
          </button>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-surface border border-border rounded-card p-6 space-y-5"
      >
        <AutocompleteInput
          label="Beschreibung"
          name="description"
          field="expense_description"
          value={form.description}
          onChange={handleChange}
          required
          placeholder="z.B. Hetzner Cloud VPS, Anthropic API, Domain .de"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Kategorie"
            name="category"
            type="select"
            value={form.category}
            onChange={handleChange}
            required
            options={categoryOptions}
          />
          <FormField
            label="Betrag"
            name="amount"
            type="number"
            value={form.amount}
            onChange={handleChange}
            required
            step="0.01"
            min={0}
            placeholder="0.00"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Datum"
            name="date"
            type="date"
            value={form.date}
            onChange={handleChange}
            required
          />
          <AutocompleteInput
            label="Anbieter"
            name="vendor"
            field="vendor"
            value={form.vendor || ''}
            onChange={handleChange}
            placeholder="z.B. Hetzner, AWS, Google"
          />
        </div>

        <div className="space-y-3">
          <Toggle
            checked={form.paid !== false}
            onChange={setPaid}
            label="Bezahlt"
            hint="Nur bezahlte Ausgaben fließen in EÜR und Jahresübersicht ein."
          />
          {form.paid !== false && (
            <FormField
              label="Zahlungsdatum"
              name="paid_at"
              type="date"
              value={form.paid_at || form.date}
              onChange={handleChange}
            />
          )}
        </div>

        <div>
          <FormField
            label="Turnus"
            name="recurrence"
            type="select"
            value={form.recurrence || ''}
            onChange={handleChange}
            options={recurrenceSelectOptions}
          />
          {equiv.monthly != null && equiv.yearly != null && (
            <p className="text-xs text-text-muted mt-1.5">
              ≈ {formatCurrency(equiv.monthly)}/Monat · {formatCurrency(equiv.yearly)}/Jahr
            </p>
          )}
        </div>

        <FormField
          label="Notizen"
          name="notes"
          type="textarea"
          value={form.notes || ''}
          onChange={handleChange}
          placeholder="Zusätzliche Informationen..."
        />

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/ausgaben')}
            className="btn-secondary"
          >
            Abbrechen
          </button>
          <button type="submit" disabled={loading} className="btn-primary" title="Ctrl+S / ⌘S">
            {loading ? 'Speichern...' : 'Speichern'}
          </button>
        </div>
      </form>

      {isEdit && id && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-text mb-3">Belege</h3>
          <FileAttachments expense_id={id} showCamera />
        </div>
      )}

      <DeleteDialog
        isOpen={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Ausgabe löschen"
        message="Soll diese Ausgabe wirklich gelöscht werden? Dieser Vorgang kann nicht rückgängig gemacht werden."
      />
    </div>
  )
}
