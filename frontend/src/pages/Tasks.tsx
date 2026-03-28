import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Task } from '../types'

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
  critical: 'bg-[#f8514933] text-danger',
  warning: 'bg-[#d2992233] text-warning',
  info: 'bg-[#58a6ff1a] text-accent',
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get('/tasks')
      .then((r) => {
        setTasks(r.data.tasks)
        setCount(r.data.count)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h2 className="text-lg font-semibold text-text">Aufgaben</h2>
        {count > 0 && (
          <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 rounded-full bg-accent text-white text-xs font-semibold">
            {count}
          </span>
        )}
      </div>

      {tasks.length === 0 ? (
        <div className="bg-surface border border-border rounded-[12px] p-12 text-center">
          <p className="text-text-muted">Keine anstehenden Aufgaben</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task, idx) => (
            <div
              key={idx}
              onClick={() => navigate(task.link)}
              className={`bg-surface border border-border rounded-[12px] p-4 pl-5 border-l-4 ${priorityColors[task.priority] || 'border-l-border'} cursor-pointer hover:bg-surface-2 transition-colors`}
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
      )}
    </div>
  )
}
