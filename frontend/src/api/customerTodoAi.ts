import { api } from './client'

/** Ein KI-Vorschlag — noch nichts angelegt. */
export interface TodoSuggestion {
  title: string
  notes: string | null
  priority: string
  due_date: string | null
  /** Woertliches Zitat aus den Kundendaten, auf das sich der Vorschlag stuetzt. */
  evidence: string
  /** Titel existiert schon als offenes To-do. */
  duplicate: boolean
}

export interface TodoSuggestionResponse {
  suggestions: TodoSuggestion[]
  /** Was die KI bzw. der Server bewusst nicht uebernommen hat, mit Grund. */
  ignored: string[]
  cached: boolean
  run: { model: string; cost_eur: number; cost_usd: number }
  budget: { budget_eur: number; spent_eur: number; remaining_eur: number; warn: boolean }
}

/**
 * Aufgaben aus den vorliegenden Kundendaten ableiten. Legt nichts an.
 *
 * Ein unveraenderter Kunde liefert den Vorschlag aus dem Cache (0 €); `force`
 * umgeht ihn. `hint` ist ein eigener Hinweis, der die Kundendaten schlaegt.
 */
export async function suggestCustomerTodos(
  customerId: string,
  opts: { force?: boolean; hint?: string } = {},
): Promise<TodoSuggestionResponse> {
  const params = new URLSearchParams()
  if (opts.force) params.set('force', 'true')
  if (opts.hint) params.set('hint', opts.hint)
  const query = params.toString()
  const response = await api.post(
    `/customers/${customerId}/todo-suggestions${query ? `?${query}` : ''}`,
    {},
    // Ein KI-Lauf braucht laenger als der Standard-Timeout des Clients.
    { timeout: 180_000 },
  )
  return response.data
}
