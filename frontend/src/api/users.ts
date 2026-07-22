import { api } from './client'

export interface AppUser {
  /** Geteilter Arbeitsbereich (Rolle „mitarbeiter"): auf wessen Daten wird gearbeitet. */
  works_for_id?: string | null
  works_for_username?: string | null
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
  works_for_id?: string | null
}): Promise<AppUser> {
  const res = await api.post('/users', data)
  return res.data
}

export async function updateUser(
  id: string,
  data: { email?: string | null; role?: string; is_active?: boolean; works_for_id?: string | null },
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

export async function getMe(): Promise<{ username: string; role: string; totp_enabled: boolean }> {
  return (await api.get('/auth/me')).data
}

export async function init2fa(): Promise<{ secret: string; otpauth_uri: string; qr: string }> {
  return (await api.get('/auth/2fa/init')).data
}

export async function enable2fa(secret: string, code: string): Promise<void> {
  await api.post('/auth/2fa/enable', { secret, code })
}

export async function disable2fa(code: string): Promise<void> {
  await api.post('/auth/2fa/disable', { code })
}
