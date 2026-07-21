import { useEffect, useState, useCallback } from 'react'
import LoadingIndicator from '../components/LoadingIndicator'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import toast from 'react-hot-toast'
import type { Task } from '../types'
import TodoList from '../components/TodoList'
import PageHeader from '../components/PageHeader'

const categoryLabels: Record<string, string> = {
  overdue_invoice: 'Überfällige Rechnung',
  due_invoice: 'Fällige Rechnung',
  draft_invoice: 'Rechnungsentwurf',
  expiring_contract: 'Vertrag läuft aus',
  active_order: 'Auftrag in Arbeit',
}

const priorityColors: Record<string, string> = {
  critical: 'border-l-red-500',
  warning: 'border-l-orange-400',
  info: 'border-l-blue-400',
}

const priorityBadgeColors: Record<string, string> = {
  critical: 'bg-danger/20 text-danger',
  warning: 'bg-warning/20 text-warning',
  info: 'bg-accent/10 text-accent',
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [openTodos, setOpenTodos] = useState(0)
  // Automatische Hinweise sind Kontext, keine Handlungsliste — daher
  // eingeklappt, Zustand überlebt den Reload.
  const [hintsOpen, setHintsOpen] = useState(
    () => localStorage.getItem('ops-tasks-hints-open') === '1'
  )
  const navigate = useNavigate()

  const toggleHints = () => {
    setHintsOpen((v) => {
      localStorage.setItem('ops-tasks-hints-open', v ? '0' : '1')
      return !v
    })
  }

  const loadTasks = useCallback(() => {
    api
      .get('/tasks')
      .then((r) => {
        setTasks(r.data.tasks)
        setCount(r.data.count)
      })
      .catch((err) => console.warn("Daten konnten nicht geladen werden:", err))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  const handleGenerateRecurring = async () => {
    setGenerating(true)
    try {
      const res = await api.post('/invoices/generate-recurring')
      const created = res.data as unknown[]
      if (created.length === 0) {
        toast('Keine fälligen Vertragsrechnungen vorhanden', { icon: 'ℹ️' })
      } else {
        toast.success(`${created.length} Vertragsrechnung${created.length > 1 ? 'en' : ''} erstellt`)
      }
      loadTasks()
    } catch {
      toast.error('Fehler beim Generieren der Vertragsrechnungen')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <LoadingIndicator />
  }

  return (
    <div>
      <PageHeader
        title="Aufgaben"
        subtitle={openTodos > 0 ? `${openTodos} offene To-dos` : 'Deine To-dos und automatische Hinweise'}
        actions={
          <button
            onClick={handleGenerateRecurring}
            disabled={generating}
            className="btn-secondary text-sm"
          >
            {generating ? 'Generiere…' : 'Vertragsrechnungen generieren'}
          </button>
        }
      />

      {/* Manuelle To-dos — die eigentliche Arbeitsliste */}
      <TodoList hideHeading onCountChange={setOpenTodos} />

      {/* Automatisch abgeleitete Hinweise aus Rechnungen/Verträgen/Aufträgen.
          Kein CRUD — daher unterhalb der To-dos und standardmäßig eingeklappt. */}
      <div className="mt-8 border-t border-border pt-5">
        <button
          onClick={toggleHints}
          aria-expanded={hintsOpen}
          className="md-state flex items-center gap-2 text-sm font-semibold text-text rounded-md px-2 py-1 -ml-2"
        >
          <svg
            className={`w-4 h-4 transition-transform duration-short ${hintsOpen ? 'rotate-90' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Automatische Hinweise
          {count > 0 && (
            <span className="inline-flex items-center justify-center min-w-[22px] h-5 px-2 rounded-full bg-surface-2 text-text-muted text-xs font-semibold">
              {count}
            </span>
          )}
        </button>
        <p className="text-xs text-text-muted mt-1 ml-6">
          Aus Rechnungen, Verträgen und Aufträgen abgeleitet — nichts zum Abhaken.
        </p>

        {hintsOpen && (tasks.length === 0 ? (
          <div className="bg-surface border border-border rounded-card p-8 text-center mt-4">
            <p className="text-text-muted text-sm">Keine offenen Hinweise</p>
          </div>
        ) : (
          <div className="space-y-3 mt-4">
          {tasks.map((task, idx) => (
            <div
              key={idx}
              onClick={() => navigate(task.link)}
              className={`bg-surface border border-border rounded-card p-4 pl-5 border-l-4 ${priorityColors[task.priority] || 'border-l-border'} cursor-pointer hover:bg-surface-2 transition-colors`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${priorityBadgeColors[task.priority] || ''}`}
                    >
                      {categoryLabels[task.type] || task.type}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-text truncate">{task.title}</p>
                  <p className="text-xs text-text-muted mt-0.5">{task.subtitle}</p>
                  <p className="text-xs text-text-muted mt-1">{task.detail}</p>
                </div>
                <div className="text-xs text-text-muted whitespace-nowrap">{task.date}</div>
              </div>
            </div>
          ))}
          </div>
        ))}
      </div>
    </div>
  )
}
