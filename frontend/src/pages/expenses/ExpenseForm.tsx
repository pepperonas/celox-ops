import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import FormField from '../../components/FormField'
import DeleteDialog from '../../components/DeleteDialog'
import FileAttachments from '../../components/FileAttachments'
import { getExpense, createExpense, updateExpense, deleteExpense } from '../../api/expenses'
import type { ExpenseCreate } from '../../types'
import { useFormShortcuts } from '../../hooks/useFormShortcuts'

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

const emptyForm: ExpenseCreate = {
  description: '',
  category: 'sonstige',
  amount: 0,
  date: new Date().toISOString().split('T')[0],
  vendor: '',
  recurring: false,
  notes: '',
}

export default function ExpenseForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [form, setForm] = useState<ExpenseCreate>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

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
          notes: e.notes || '',
        }),
      )
    }
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const target = e.target
    if (target instanceof HTMLInputElement && target.type === 'checkbox') {
      setForm({ ...form, [target.name]: target.checked })
    } else if (target.name === 'amount') {
      setForm({ ...form, amount: parseFloat(target.value) || 0 })
    } else {
      setForm({ ...form, [target.name]: target.value })
    }
  }

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
      if (isEdit) {
        await updateExpense(id!, form)
        toast.success('Ausgabe aktualisiert.')
      } else {
        await createExpense(form)
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
    try {
      await deleteExpense(id)
      toast.success('Ausgabe gelöscht.')
      navigate('/ausgaben')
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
        {isEdit && (
          <button onClick={() => setShowDelete(true)} className="btn-danger">
            Löschen
          </button>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-surface border border-border rounded-card p-6 space-y-5"
      >
        <FormField
          label="Beschreibung"
          name="description"
          value={form.description}
          onChange={handleChange}
          required
          placeholder="z.B. Hetzner Cloud Server"
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
          <FormField
            label="Anbieter"
            name="vendor"
            value={form.vendor || ''}
            onChange={handleChange}
            placeholder="z.B. Hetzner, AWS, Google"
          />
        </div>

        <FormField
          label="Wiederkehrend"
          name="recurring"
          type="checkbox"
          value={form.recurring || false}
          onChange={handleChange}
        />

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
