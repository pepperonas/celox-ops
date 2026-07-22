import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  getUsers, createUser, updateUser, setUserPassword, deleteUser, type AppUser,
} from '../api/users'
import { useAuthStore } from '../store/authStore'
import DeleteDialog from '../components/DeleteDialog'
import Select from '../components/Select'

export default function Users() {
  const me = useAuthStore((s) => s.username)
  const [users, setUsers] = useState<AppUser[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', email: '', role: 'user', works_for_id: '' })
  const [saving, setSaving] = useState(false)
  const [toDelete, setToDelete] = useState<AppUser | null>(null)

  const load = async () => {
    try {
      setUsers(await getUsers())
    } catch {
      toast.error('Benutzer konnten nicht geladen werden.')
    }
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password.length < 8) { toast.error('Passwort min. 8 Zeichen.'); return }
    setSaving(true)
    try {
      await createUser({ username: form.username.trim(), password: form.password, email: form.email.trim() || null, role: form.role, works_for_id: form.role === 'mitarbeiter' ? form.works_for_id || null : null })
      toast.success('Benutzer angelegt.')
      setShowForm(false)
      setForm({ username: '', password: '', email: '', role: 'user', works_for_id: '' })
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Anlegen fehlgeschlagen.')
    }
    setSaving(false)
  }

  const toggleActive = async (u: AppUser) => {
    try {
      await updateUser(u.id, { is_active: !u.is_active })
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Aktion fehlgeschlagen.')
    }
  }

  const changeRole = async (u: AppUser, role: string) => {
    try {
      await updateUser(u.id, { role })
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Rolle konnte nicht geändert werden.')
    }
  }

  const resetPw = async (u: AppUser) => {
    const pw = window.prompt(`Neues Passwort für ${u.username} (min. 8 Zeichen):`)
    if (!pw) return
    if (pw.length < 8) { toast.error('Passwort min. 8 Zeichen.'); return }
    try {
      await setUserPassword(u.id, pw)
      toast.success('Passwort gesetzt.')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Fehlgeschlagen.')
    }
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      await deleteUser(toDelete.id)
      toast.success('Benutzer gelöscht.')
      setToDelete(null)
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Löschen fehlgeschlagen.')
      setToDelete(null)
    }
  }

  if (loading) return <div className="text-text-muted text-sm">Lade Benutzer…</div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-text tracking-tight">Benutzer</h2>
          <p className="text-text-muted text-sm mt-1">
            Jeder Benutzer hat einen eigenen, isolierten Arbeitsbereich. Konten werden nur hier (durch Admins) angelegt.
          </p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-primary">
          {showForm ? 'Abbrechen' : 'Benutzer anlegen'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-surface border border-border rounded-card p-5 mb-6 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">Benutzername</label>
            <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required minLength={3} className="w-full" />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">E-Mail (optional)</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full" />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Passwort (min. 8)</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} className="w-full" />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Rolle</label>
            <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full"
              options={[
                { value: 'user', label: 'Benutzer (eigener Bereich)' },
                { value: 'mitarbeiter', label: 'Mitarbeiter (fremder Bereich, kein Löschen)' },
                { value: 'admin', label: 'Admin' },
              ]}
            />
          </div>
          {form.role === 'mitarbeiter' && (
            <div>
              <label className="block text-xs text-text-muted mb-1">Arbeitet im Bereich von</label>
              <Select
                value={form.works_for_id}
                onChange={(e) => setForm({ ...form, works_for_id: e.target.value })}
                className="w-full"
                placeholder="— bitte wählen —"
                options={users.filter((u) => !u.works_for_id).map((u) => ({ value: u.id, label: u.username }))}
              />
              <p className="text-[11px] text-text-muted mt-1">
                Sieht und bearbeitet die Daten dieses Kontos — kann aber nichts löschen oder zusammenführen.
              </p>
            </div>
          )}
          <div className="sm:col-span-2">
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Speichere…' : 'Anlegen'}</button>
          </div>
        </form>
      )}

      <div className="bg-surface border border-border rounded-card divide-y divide-border">
        {users.map((u) => (
          <div key={u.id} className="flex items-center gap-3 p-4 flex-wrap">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text truncate">{u.username}</span>
                {u.username === me && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent">du</span>}
                {!u.is_active && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-danger/15 text-danger">deaktiviert</span>}
              </div>
              {u.email && <span className="text-xs text-text-muted">{u.email}</span>}
              {u.works_for_username && (
                <span className="block text-xs text-text-muted">
                  arbeitet im Bereich von <span className="text-text">{u.works_for_username}</span>
                </span>
              )}
            </div>
            <Select
              value={u.role}
              onChange={(e) => changeRole(u, e.target.value)}
              disabled={u.username === me}
              className="!w-auto !py-1.5 !text-sm"
              title={u.username === me ? 'Eigene Rolle nicht änderbar' : 'Rolle'}
              options={[
                { value: 'user', label: 'Benutzer' },
                { value: 'mitarbeiter', label: 'Mitarbeiter' },
                { value: 'admin', label: 'Admin' },
              ]}
            />
            <button onClick={() => resetPw(u)} className="text-xs px-2.5 py-1 rounded-lg bg-surface-2 text-text hover:bg-border">Passwort</button>
            {u.username !== me && (
              <>
                <button onClick={() => toggleActive(u)} className="text-xs px-2.5 py-1 rounded-lg bg-surface-2 text-text hover:bg-border">
                  {u.is_active ? 'Deaktivieren' : 'Aktivieren'}
                </button>
                <button onClick={() => setToDelete(u)} className="text-xs px-2.5 py-1 rounded-lg text-danger hover:bg-danger/10">Löschen</button>
              </>
            )}
          </div>
        ))}
      </div>

      <DeleteDialog
        isOpen={!!toDelete}
        onClose={() => setToDelete(null)}
        onConfirm={confirmDelete}
        title="Benutzer löschen"
        message={`Benutzer "${toDelete?.username}" und dessen kompletten Arbeitsbereich (alle Kunden, Rechnungen usw.) unwiderruflich löschen?`}
      />
    </div>
  )
}
