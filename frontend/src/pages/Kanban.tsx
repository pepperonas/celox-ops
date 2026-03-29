import { useEffect, useState, useCallback } from 'react'
import { getOrders, updateOrder } from '../api/orders'
import { formatCurrency } from '../utils/formatters'
import toast from 'react-hot-toast'
import type { Order, OrderStatus } from '../types'

interface KanbanColumn {
  status: OrderStatus
  label: string
  color: string
  borderColor: string
}

const COLUMNS: KanbanColumn[] = [
  { status: 'angebot', label: 'Angebot', color: '#c9a227', borderColor: '#c9a227' },
  { status: 'beauftragt', label: 'Beauftragt', color: '#58a6ff', borderColor: '#58a6ff' },
  { status: 'in_arbeit', label: 'In Arbeit', color: '#a371f7', borderColor: '#a371f7' },
  { status: 'abgeschlossen', label: 'Abgeschlossen', color: '#3fb950', borderColor: '#3fb950' },
]

export default function Kanban() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOverColumn, setDragOverColumn] = useState<OrderStatus | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const fetchOrders = useCallback(async () => {
    try {
      const res = await getOrders({ page_size: 1000 })
      setOrders(res.items)
    } catch {
      toast.error('Fehler beim Laden der Aufträge.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  const handleDragStart = (e: React.DragEvent, orderId: string) => {
    e.dataTransfer.setData('text/plain', orderId)
    e.dataTransfer.effectAllowed = 'move'
    setDraggingId(orderId)
  }

  const handleDragEnd = () => {
    setDraggingId(null)
    setDragOverColumn(null)
  }

  const handleDragOver = (e: React.DragEvent, status: OrderStatus) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(status)
  }

  const handleDragLeave = () => {
    setDragOverColumn(null)
  }

  const handleDrop = async (e: React.DragEvent, newStatus: OrderStatus) => {
    e.preventDefault()
    setDragOverColumn(null)
    setDraggingId(null)

    const orderId = e.dataTransfer.getData('text/plain')
    const order = orders.find((o) => o.id === orderId)
    if (!order || order.status === newStatus) return

    // Optimistic update
    setOrders((prev) =>
      prev.map((o) => (o.id === orderId ? { ...o, status: newStatus } : o))
    )

    try {
      await updateOrder(orderId, { status: newStatus })
      toast.success(`Auftrag nach "${COLUMNS.find((c) => c.status === newStatus)?.label}" verschoben.`)
    } catch {
      toast.error('Fehler beim Aktualisieren.')
      fetchOrders()
    }
  }

  const ordersByStatus = (status: OrderStatus) =>
    orders.filter((o) => o.status === status)

  if (loading) {
    return <div className="text-text-muted py-12 text-center">Laden...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-text">Kanban-Board</h2>
        <span className="text-sm text-text-muted">{orders.length} Aufträge</span>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: 'calc(100vh - 200px)' }}>
        {COLUMNS.map((col) => {
          const colOrders = ordersByStatus(col.status)
          const isDragOver = dragOverColumn === col.status

          return (
            <div
              key={col.status}
              className="flex-1 min-w-[260px] flex flex-col"
              onDragOver={(e) => handleDragOver(e, col.status)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, col.status)}
            >
              {/* Column header */}
              <div
                className="rounded-t-[8px] px-4 py-2.5 flex items-center justify-between"
                style={{ backgroundColor: col.color + '20', borderTop: `3px solid ${col.borderColor}` }}
              >
                <span className="text-sm font-semibold" style={{ color: col.color }}>
                  {col.label}
                </span>
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: col.color + '25', color: col.color }}
                >
                  {colOrders.length}
                </span>
              </div>

              {/* Column body */}
              <div
                className={`flex-1 bg-surface border border-border rounded-b-[8px] p-3 space-y-3 transition-all duration-150 ${
                  isDragOver ? 'border-accent border-dashed bg-[#58a6ff08]' : ''
                }`}
              >
                {colOrders.length === 0 && (
                  <div className="text-center text-text-muted text-xs py-8">
                    Keine Aufträge
                  </div>
                )}
                {colOrders.map((order) => (
                  <div
                    key={order.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, order.id)}
                    onDragEnd={handleDragEnd}
                    className={`bg-surface-2 border border-border rounded-[6px] p-3 cursor-grab active:cursor-grabbing transition-all duration-150 hover:border-text-muted ${
                      draggingId === order.id ? 'opacity-40' : ''
                    }`}
                  >
                    <div className="text-sm font-medium text-text mb-1 line-clamp-2">
                      {order.title}
                    </div>
                    {order.customer_name && (
                      <div className="text-xs text-text-muted mb-1.5">
                        {order.customer_name}
                      </div>
                    )}
                    <div className="flex items-center justify-between text-xs text-text-muted">
                      {order.amount ? (
                        <span className="font-medium tabular-nums" style={{ color: col.color }}>
                          {formatCurrency(order.amount)}
                        </span>
                      ) : (
                        <span>&ndash;</span>
                      )}
                      <span>
                        {order.start_date
                          ? new Date(order.start_date).toLocaleDateString('de-DE', {
                              day: '2-digit',
                              month: '2-digit',
                              year: '2-digit',
                            })
                          : new Date(order.created_at).toLocaleDateString('de-DE', {
                              day: '2-digit',
                              month: '2-digit',
                              year: '2-digit',
                            })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
