import { api } from './client'

export interface RefValue {
  value: string
  count: number
  custom: boolean
  created_at: string | null
}
export interface RefField {
  key: string
  label: string
}

export async function getRefFields(): Promise<RefField[]> {
  const r = await api.get('/reference-values/fields')
  return r.data.fields
}

export async function getRefValues(field: string): Promise<RefValue[]> {
  const r = await api.get('/reference-values', { params: { field } })
  return r.data.values
}

export async function createRefValue(field: string, value: string): Promise<string> {
  const r = await api.post('/reference-values', { field, value })
  return r.data.value
}

export async function renameRefValue(
  field: string, oldValue: string, newValue: string,
): Promise<{ affected: number; value: string }> {
  const r = await api.post('/reference-values/rename', { field, old: oldValue, new: newValue })
  return r.data
}

export async function deleteRefValue(
  field: string, value: string, replaceWith?: string | null,
): Promise<{ affected: number; replaced: string | null }> {
  const r = await api.delete('/reference-values', {
    data: { field, value, replace_with: replaceWith || null },
  })
  return r.data
}
