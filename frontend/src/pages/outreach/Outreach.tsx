import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import SegmentedButtons from '../../components/SegmentedButtons'
import FilterChips from '../../components/FilterChips'
import LoadingIndicator from '../../components/LoadingIndicator'
import type { OutreachChannel, OutreachTemplate } from '../../types'
import {
  getOutreachTemplates,
  seedOutreachTemplates,
  updateOutreachTemplate,
  deleteOutreachTemplate,
} from '../../api/outreach'
import { CATEGORIES, CHANNELS } from './constants'
import TemplateCard from './TemplateCard'
import CopyModal from './CopyModal'
import TemplateFormModal from './TemplateFormModal'

const SEED_FLAG = 'outreach-seed-checked'

export default function Outreach() {
  const [all, setAll] = useState<OutreachTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [channel, setChannel] = useState<OutreachChannel>('email')
  const [category, setCategory] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [copying, setCopying] = useState<OutreachTemplate | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<OutreachTemplate | null>(null)
  const [seeding, setSeeding] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        let items = await getOutreachTemplates()
        // Erstbesuch (leer) ODER neue Rubrik-Linie fehlt → einmalig (pro Session)
        // additiv nachziehen. Der Seed-Endpoint fügt nur fehlende Rubriken hinzu.
        const cats = new Set(items.map((t) => t.category))
        const missingLine = CATEGORIES.some((c) => !cats.has(c.value))
        if ((items.length === 0 || missingLine) && !sessionStorage.getItem(SEED_FLAG)) {
          sessionStorage.setItem(SEED_FLAG, '1')
          items = await seedOutreachTemplates()
        }
        setAll(items)
      } catch {
        toast.error('Vorlagen konnten nicht geladen werden.')
      }
      setLoading(false)
    })()
  }, [])

  const runSeed = async () => {
    setSeeding(true)
    try {
      setAll(await seedOutreachTemplates())
      toast.success('Vorlagen geladen.')
    } catch {
      toast.error('Laden fehlgeschlagen.')
    }
    setSeeding(false)
  }

  const upsert = (t: OutreachTemplate) =>
    setAll((prev) => (prev.some((x) => x.id === t.id) ? prev.map((x) => (x.id === t.id ? t : x)) : [...prev, t]))

  const toggleFavorite = async (t: OutreachTemplate) => {
    const next = !t.is_favorite
    setAll((prev) => prev.map((x) => (x.id === t.id ? { ...x, is_favorite: next } : x)))
    try {
      await updateOutreachTemplate(t.id, { is_favorite: next })
    } catch {
      toast.error('Favorit konnte nicht geändert werden.')
      setAll((prev) => prev.map((x) => (x.id === t.id ? { ...x, is_favorite: !next } : x)))
    }
  }

  const remove = async (t: OutreachTemplate) => {
    if (!window.confirm(`Template „${t.title}" löschen?`)) return
    setAll((prev) => prev.filter((x) => x.id !== t.id))
    try {
      await deleteOutreachTemplate(t.id)
      toast.success('Gelöscht.')
    } catch {
      toast.error('Löschen fehlgeschlagen.')
      setAll((prev) => [...prev, t])
    }
  }

  const bumpUsage = (id: string) =>
    setAll((prev) => prev.map((x) => (x.id === id ? { ...x, usage_count: x.usage_count + 1 } : x)))

  const q = search.trim().toLowerCase()
  const searchResults = useMemo(() => {
    if (!q) return null
    return all.filter((t) =>
      t.title.toLowerCase().includes(q)
      || (t.subject || '').toLowerCase().includes(q)
      || t.body.toLowerCase().includes(q),
    )
  }, [all, q])

  const favorites = useMemo(() => all.filter((t) => t.is_favorite), [all])
  const channelTemplates = useMemo(
    () => all.filter((t) => t.channel === channel && (category === 'all' || t.category === category)),
    [all, channel, category],
  )

  const categoryChips = [{ value: 'all', label: 'Alle' }, ...CATEGORIES.map((c) => ({ value: c.value, label: c.label }))]

  const cardHandlers = {
    onCopy: setCopying,
    onEdit: (t: OutreachTemplate) => { setEditing(t); setFormOpen(true) },
    onToggleFavorite: toggleFavorite,
    onDelete: remove,
  }

  return (
    <div className="pb-24">
      <PageHeader title="Akquise-Nachrichten" subtitle={`${all.length} Vorlagen · IT-Security first`} />

      {/* Suche (kanalübergreifend) */}
      <div className="mb-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Alle Vorlagen durchsuchen (Titel, Betreff, Text)…"
          className="w-full"
        />
      </div>

      {loading ? (
        <LoadingIndicator />
      ) : all.length === 0 ? (
        <div className="text-center py-16 text-text-muted">
          <p className="mb-4">Noch keine Vorlagen.</p>
          <button onClick={runSeed} disabled={seeding} className="btn-primary">
            {seeding ? 'Lade…' : 'Standard-Vorlagen laden'}
          </button>
        </div>
      ) : searchResults ? (
        // ---- Suchansicht: flach, kanalübergreifend ----
        <>
          <p className="text-xs text-text-muted mb-3">{searchResults.length} Treffer für „{search}"</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchResults.map((t) => <TemplateCard key={t.id} template={t} showChannel {...cardHandlers} />)}
          </div>
        </>
      ) : (
        <>
          {/* Favoriten (kanalübergreifend, oben) */}
          {favorites.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-semibold text-text mb-2">★ Favoriten</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {favorites.map((t) => <TemplateCard key={t.id} template={t} showChannel {...cardHandlers} />)}
              </div>
            </section>
          )}

          {/* Kanal-Tabs */}
          <div className="mb-4 overflow-x-auto">
            <SegmentedButtons
              options={CHANNELS.map((c) => ({ value: c.value, label: `${c.icon} ${c.label}` }))}
              value={channel}
              onChange={setChannel}
            />
          </div>

          {/* Rubriken-Filter */}
          <div className="mb-4">
            <FilterChips options={categoryChips} value={category} onChange={setCategory} />
          </div>

          {channelTemplates.length === 0 ? (
            <p className="text-center py-12 text-text-muted text-sm">Keine Vorlagen in dieser Rubrik.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {channelTemplates.map((t) => <TemplateCard key={t.id} template={t} {...cardHandlers} />)}
            </div>
          )}
        </>
      )}

      <footer className="mt-12 pt-6 border-t border-border text-center text-xs text-text-muted">
        © 2026 Martin Pfeffer | celox.io
      </footer>

      <Fab onClick={() => { setEditing(null); setFormOpen(true) }} label="Neues Template" />

      {copying && (
        <CopyModal template={copying} onClose={() => setCopying(null)} onCopied={bumpUsage} />
      )}
      {formOpen && (
        <TemplateFormModal
          template={editing}
          initialChannel={channel}
          onClose={() => { setFormOpen(false); setEditing(null) }}
          onSaved={(t) => { upsert(t); setFormOpen(false); setEditing(null) }}
        />
      )}
    </div>
  )
}
