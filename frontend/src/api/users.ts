import { api } from './client'

export interface AppUser {
  id: string
  username: string
  email: string | null
  role: string
  is_active: boolean
  created_at: string
}

export async function getUsers(): Promise<AppUser[]> {
  const res = await api.get('/users')
  return res.data
}

export async function createUser(data: {
  username: string
  password: string
  email?: string | null
  role: string
}): Promise<AppUser> {
  const res = await api.post('/users', data)
  return res.data
}

export async function updateUser(
  id: string,
  data: { email?: string | null; role?: string; is_active?: boolean },
): Promise<AppUser> {
  const res = await api.patch(`/users/${id}`, data)
  return res.data
}

export async function setUserPassword(id: string, password: string): Promise<void> {
  await api.post(`/users/${id}/password`, { password })
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/users/${id}`)
}

export async function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  await api.post('/users/me/password', { current_password: currentPassword, new_password: newPassword })
}

export async function getMyIcalToken(): Promise<string> {
  const res = await api.get('/users/me/ical-token')
  return res.data.token
}
