import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, LayoutGroup, motion, MotionConfig } from 'motion/react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/PageHeader'
import Fab from '../../components/Fab'
import SegmentedButtons from '../../components/SegmentedButtons'
import FilterChips from '../../components/FilterChips'
import LoadingIndicator from '../../components/LoadingIndicator'
import type { OutreachChannel, OutreachTemplate } from '../../types'
import {
  getOutreachTemplates,
  reorderOutreachFavorites,
  reorderOutreachTemplates,
  seedOutreachTemplates,
  updateOutreachTemplate,
  deleteOutreachTemplate,
} from '../../api/outreach'
import { applyVisibleOrder, moveBy, moveItem, orderIds, sortFavorites } from './cardOrder'
import SpeakingCardDialog from './SpeakingCardDialog'
import {
  CATEGORIES, CATEGORY_AXIS, CHANNELS,
  restoreCategory, restoreChannel, restoreFavoritesOpen,
} from './constants'
import TemplateCard from './TemplateCard'
import CopyModal from './CopyModal'
import TemplateFormModal from './TemplateFormModal'
import Icon from '../../components/Icon'
import { T } from '../../utils/motionTokens'
import { useAuthStore } from '../../store/authStore'
import { canEditOutreachTemplates } from '../../utils/permissions'

const SEED_FLAG = 'outreach-seed-checked'
// Kanal und Rubrik überleben Reload und Zurück-Navigation — gleiches Muster wie
// die Pipeline-Filter. Die Suche bleibt bewusst flüchtig: ein wiederhergestellter
// Suchbegriff sähe nach dem Laden wie ein leerer Vorlagenbestand aus.
const CHANNEL_KEY = 'akquise-channel'
const CATEGORY_KEY = 'akquise-category'
const FAVORITES_OPEN_KEY = 'akquise-favorites-open'

export default function Outreach() {
  const [all, setAll] = useState<OutreachTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [channel, setChannel] = useState<OutreachChannel>(
    () => restoreChannel(localStorage.getItem(CHANNEL_KEY)),
  )
  const [category, setCategory] = useState<string>(
    () => restoreCategory(localStorage.getItem(CATEGORY_KEY)),
  )
  const [search, setSearch] = useState('')
  const [copying, setCopying] = useState<OutreachTemplate | null>(null)
  const [speaking, setSpeaking] = useState<OutreachTemplate | null>(null)
  // Index der gezogenen Karte innerhalb der SICHTBAREN Liste (s. applyVisibleOrder).
  const [dragFrom, setDragFrom] = useState<number | null>(null)
  const [favDragFrom, setFavDragFrom] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<OutreachTemplate | null>(null)
  const [seeding, setSeeding] = useState(false)
  const [favoritesOpen, setFavoritesOpen] = useState(
    () => restoreFavoritesOpen(localStorage.getItem(FAVORITES_OPEN_KEY)),
  )
  // Verkäufer dürfen Vorlagen lesen und kopieren, aber nicht ändern. Der Server
  // lehnt Schreibzugriffe ohnehin ab (403) — hier verschwinden die Knöpfe, damit
  // niemand ins Leere klickt.
  const mayEdit = canEditOutreachTemplates(useAuthStore((st) => st.role))

  useEffect(() => {
    (async () => {
      try {
        let items = await getOutreachTemplates()
        // Erstbesuch (leer) ODER eine ganze Rubrik fehlt → einmalig pro Session
        // nachziehen. Der Endpunkt ergänzt inzwischen je EINZELNE Vorlage; eine
        // neue Serie innerhalb bestehender Rubriken löst diesen Automatismus
        // aber nicht aus — dafür gibt es den Knopf „Vorlagen ergänzen“.
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

  /**
   * Nach einem Filterwechsel muss das Ergebnis SICHTBAR sein.
   *
   * Wer in einer langen Rubrik weit unten stand und dann auf eine kurze filtert,
   * schaute ins Leere: Die neue Liste ist oben, der Blick war unten, und der
   * Browser behält die Scrollposition (bzw. klemmt sie, was zusätzlich springt).
   * Deshalb holt der Wechsel die Filterleiste zurück in den Blick.
   *
   * `block: 'nearest'` ist der Punkt: Ist die Leiste schon sichtbar, passiert
   * NICHTS — kein unmotiviertes Springen bei jedem Chip-Klick. Und ohne `smooth`,
   * weil animiertes Scrollen gegen die einblendende Liste arbeitet (dieselbe
   * Lehre wie beim FLIP der To-do-Liste).
   *
   * Nicht beim ersten Rendern: Da wäre es ein Sprung ohne Anlass.
   */
  const filterBarRef = useRef<HTMLDivElement>(null)
  const ersterLauf = useRef(true)
  useEffect(() => {
    if (ersterLauf.current) { ersterLauf.current = false; return }
    filterBarRef.current?.scrollIntoView({ block: 'nearest' })
  }, [channel, category])

  useEffect(() => { localStorage.setItem(CHANNEL_KEY, channel) }, [channel])
  useEffect(() => {
    localStorage.setItem(FAVORITES_OPEN_KEY, favoritesOpen ? '1' : '0')
  }, [favoritesOpen])
  useEffect(() => {
    // „Alle Rubriken" ist der Standard und braucht keinen Eintrag — so bleibt der
    // Speicher leer, solange nichts gefiltert ist.
    if (category === 'all') localStorage.removeItem(CATEGORY_KEY)
    else localStorage.setItem(CATEGORY_KEY, category)
  }, [category])

  // Zieht fehlende Standard-Vorlagen nach — additiv je Vorlage, nicht je Rubrik.
  // Nötig, weil neue Serien innerhalb einer bestehenden Rubrik den
  // Arbeitsbereich sonst nie erreichen (der Auto-Seed prüft nur auf fehlende
  // Rubriken). Bestehende Vorlagen inkl. Favoriten/Zähler bleiben unangetastet.
  const runSeed = async () => {
    setSeeding(true)
    const vorher = all.length
    try {
      const items = await seedOutreachTemplates()
      setAll(items)
      const neu = items.length - vorher
      toast.success(neu > 0
        ? `${neu} Vorlage${neu === 1 ? '' : 'n'} ergänzt.`
        : 'Alle Standard-Vorlagen sind vorhanden.')
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

  const setColor = async (t: OutreachTemplate, color: string | null) => {
    setAll((prev) => prev.map((x) => (x.id === t.id ? { ...x, color } : x)))
    try {
      await updateOutreachTemplate(t.id, { color })
    } catch {
      toast.error('Farbe konnte nicht gespeichert werden.')
      setAll((prev) => prev.map((x) => (x.id === t.id ? { ...x, color: t.color } : x)))
    }
  }

  /**
   * Speichert eine neue Reihenfolge. Gezogen wird in der gefilterten Ansicht, die
   * Reihenfolge gilt aber je Kanal — `applyVisibleOrder` setzt die sichtbaren
   * Karten auf ihre bisherigen Plätze zurück und lässt die übrigen unberührt.
   */
  const persistOrder = async (neueSicht: OutreachTemplate[]) => {
    const kanalVoll = all.filter((x) => x.channel === channel)
    const neuVoll = applyVisibleOrder(kanalVoll, neueSicht)
    const andere = all.filter((x) => x.channel !== channel)
    setAll([...andere, ...neuVoll])          // optimistisch
    try {
      setAll(await reorderOutreachTemplates(channel, orderIds(neuVoll)))
    } catch {
      toast.error('Reihenfolge konnte nicht gespeichert werden.')
      setAll([...andere, ...kanalVoll])
    }
  }

  /** Speichert die Reihenfolge der Favoriten. Kein Zurückrechnen nötig — die
   *  Sektion zeigt immer ALLE Favoriten, es gibt dort keinen Filter. */
  const persistFavoriteOrder = async (neu: OutreachTemplate[]) => {
    const vorher = all
    setAll((prev) => prev.map((x) => {
      const i = neu.findIndex((f) => f.id === x.id)
      return i === -1 ? x : { ...x, favorite_order: i }
    }))
    try {
      setAll(await reorderOutreachFavorites(orderIds(neu)))
    } catch {
      toast.error('Reihenfolge der Favoriten konnte nicht gespeichert werden.')
      setAll(vorher)
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

  // Favoriten haben ihre EIGENE Reihenfolge (favorite_order): die Sektion ist
  // kanalübergreifend, sort_order zählt je Kanal ab 0 — geerbt stünden die Karten
  // dort willkürlich.
  const favorites = useMemo(
    () => sortFavorites(all.filter((t) => t.is_favorite)),
    [all],
  )
  const channelTemplates = useMemo(
    () => all.filter((t) => t.channel === channel && (category === 'all' || t.category === category)),
    [all, channel, category],
  )

  // Zwei Achsen, zwei Reihen (s. CATEGORY_AXIS in constants.ts). „Alle" gehört
  // zu KEINER der beiden und steht deshalb in einer eigenen Zeile ohne Label —
  // unter der Beschriftung „Anlass" gelesen hieße es „alle Anlässe", zeigt aber
  // auch die Angebote.
  const resetChip = [{ value: 'all', label: 'Alle Rubriken' }]
  const occasionChips = CATEGORIES.filter((c) => CATEGORY_AXIS[c.value] === 'anlass')
    .map((c) => ({ value: c.value as string, label: c.label }))
  const offerChips = CATEGORIES.filter((c) => CATEGORY_AXIS[c.value] === 'angebot')
    .map((c) => ({ value: c.value as string, label: c.label }))

  const cardHandlers = {
    onCopy: setCopying,
    onEdit: (t: OutreachTemplate) => { setEditing(t); setFormOpen(true) },
    onToggleFavorite: toggleFavorite,
    onDelete: remove,
    onSpeak: setSpeaking,
    onColor: setColor,
    mayEdit,
  }

  return (
    // `reducedMotion="user"` ist der Riegel für ALLE motion-Animationen dieser
    // Seite: Bei `prefers-reduced-motion` fallen Transform- und Layout-
    // Animationen weg, Deckkraft bleibt. Ohne das wäre die neue Bewegung die
    // einzige in der App, die sich über die Systemeinstellung hinwegsetzt —
    // index.css schaltet CSS-Animationen dort global ab. anime.js fragt separat
    // (s. prefersReducedMotion in TemplateCard).
    <MotionConfig reducedMotion="user">
    <div className="pb-24">
      <PageHeader
        title="Nachrichten-Vorlagen"
        subtitle={`${all.length} Akquise-Vorlagen · IT-Security first`}
        actions={mayEdit && all.length > 0 ? (
          <button onClick={runSeed} disabled={seeding} className="btn-secondary text-sm"
                  title="Fehlende Standard-Vorlagen nachziehen — bestehende bleiben unverändert">
            {seeding ? 'Prüfe…' : 'Vorlagen ergänzen'}
          </button>
        ) : undefined}
      />

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
          {mayEdit ? (
            <button onClick={runSeed} disabled={seeding} className="btn-primary">
              {seeding ? 'Lade…' : 'Standard-Vorlagen laden'}
            </button>
          ) : (
            <p className="text-sm">Der Kontoinhaber legt die Vorlagen an.</p>
          )}
        </div>
      ) : searchResults ? (
        // ---- Suchansicht: flach, kanalübergreifend ----
        <>
          <p className="text-xs text-text-muted mb-3">{searchResults.length} Treffer für „{search}"</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
            {searchResults.map((t) => <TemplateCard key={t.id} template={t} showChannel {...cardHandlers} />)}
          </div>
        </>
      ) : (
        <>
          {/* Favoriten (kanalübergreifend, oben) — einklappbar, Zustand überlebt
              den Reload. Die Anzahl steht im Kopf, damit die zugeklappte Sektion
              noch etwas aussagt statt nur zu verschwinden. */}
          {favorites.length > 0 && (
            <section className="mb-6">
              <button
                onClick={() => setFavoritesOpen((v) => !v)}
                aria-expanded={favoritesOpen}
                className="md-state flex items-center gap-1.5 text-sm font-semibold text-text
                           rounded-md px-2 py-1 -ml-2 mb-2"
              >
                <Icon
                  name="chevronRight"
                  size={16}
                  className={`transition-transform duration-short ease-spring ${
                    favoritesOpen ? 'rotate-90' : ''
                  }`}
                />
                <Icon name="star" size={15} filled />
                Favoriten
                <span className="inline-flex items-center justify-center min-w-[22px] h-5 px-2
                                 rounded-full bg-surface-2 text-text-muted text-xs font-semibold">
                  {favorites.length}
                </span>
              </button>
              <AnimatePresence initial={false}>
              {favoritesOpen && (
                <motion.div
                  key="favgrid"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={T.spatialFast}
                  className="overflow-hidden"
                >
                {/* Eigene Gruppe mit festem Namen: Die Favoriten sind
                    kanaluebergreifend, ihre Liste haengt NICHT am Filter. Ohne
                    Gruppe lagen ihre Karten mit den Kanal-Karten in einem Topf. */}
                <LayoutGroup id="favoriten">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
                  {favorites.map((t, i) => (
                    <TemplateCard
                      key={t.id}
                      template={t}
                      showChannel
                      {...cardHandlers}
                      draggable={mayEdit}
                      onDragStartCard={() => setFavDragFrom(i)}
                      onDropOnCard={() => {
                        if (favDragFrom === null || favDragFrom === i) return
                        void persistFavoriteOrder(moveItem(favorites, favDragFrom, i))
                        setFavDragFrom(null)
                      }}
                      onMoveBy={mayEdit
                        ? (karte, delta) => {
                          const von = favorites.findIndex((x) => x.id === karte.id)
                          if (von < 0) return
                          void persistFavoriteOrder(moveBy(favorites, von, delta))
                        }
                        : undefined}
                    />
                  ))}
                </div>
                </LayoutGroup>
                </motion.div>
              )}
              </AnimatePresence>
            </section>
          )}

          {/* Kanal-Tabs. Der Ref sitzt hier, weil der Wechsel diese Leiste in den
              Blick holt — sie ist der Ort, an dem gerade geklickt wurde. */}
          <div ref={filterBarRef} className="mb-4 overflow-x-auto">
            <SegmentedButtons
              options={CHANNELS.map((c) => ({ value: c.value, label: c.label }))}
              value={channel}
              onChange={setChannel}
            />
          </div>

          {/* Rubriken-Filter: Anlass (wann) und Angebot (was) getrennt. Jede
              Reihe kennt nur ihre Optionen — die aktive Auswahl leuchtet daher
              automatisch nur in der Reihe, zu der sie gehört. */}
          <div className="mb-4 space-y-2">
            <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
              {/* Leerer Spacer in Label-Breite: hält die Chips aller drei Zeilen
                  auf einer Kante, ohne dem Reset eine Achse anzudichten. */}
              <span className="shrink-0 w-14" aria-hidden="true" />
              <FilterChips options={resetChip} value={category} onChange={setCategory} />
            </div>
            <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
              <span className="text-[11px] text-text-muted shrink-0 pt-2 w-14">Anlass</span>
              <FilterChips options={occasionChips} value={category} onChange={setCategory} />
            </div>
            <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
              <span className="text-[11px] text-text-muted shrink-0 pt-2 w-14">Angebot</span>
              <FilterChips options={offerChips} value={category} onChange={setCategory} accent />
            </div>
          </div>

          {channelTemplates.length === 0 ? (
            <p className="text-center py-12 text-text-muted text-sm">Keine Vorlagen in dieser Rubrik.</p>
          ) : (
            /* Filterwechsel ist ein SCHNITT, kein Umzug.
             *
             * Der `key` aus Kanal + Rubrik tauscht den Teilbaum aus. Damit gibt es
             * für die Karten keine „vorherige Position" — vorher animierte `layout`
             * über den Filterwechsel hinweg und ließ Karten quer über die Seite
             * fliegen, teils von außerhalb des Bildes. Innerhalb desselben Filters
             * (Ziehen, Pfeile) bleibt der Key gleich, also gleiten sie dort weiter.
             *
             * Nur Deckkraft, kein Versatz und keine Staffelung: Bei 42 Karten kam
             * die letzte knapp 800 ms nach dem Klick — das ist Warten, nicht
             * Rückmeldung. */
            <motion.div
              key={`${channel}|${category}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={T.effectDefault}
            >
            <LayoutGroup id={`kanal-${channel}-${category}`}>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
              {channelTemplates.map((t, i) => (
                <TemplateCard
                  key={t.id}
                  template={t}
                  {...cardHandlers}
                  draggable={mayEdit}
                  onDragStartCard={() => setDragFrom(i)}
                  onDropOnCard={() => {
                    if (dragFrom === null || dragFrom === i) return
                    void persistOrder(moveItem(channelTemplates, dragFrom, i))
                    setDragFrom(null)
                  }}
                  onMoveBy={mayEdit
                    ? (karte, delta) => {
                      const von = channelTemplates.findIndex((x) => x.id === karte.id)
                      if (von < 0) return
                      void persistOrder(moveBy(channelTemplates, von, delta))
                    }
                    : undefined}
                />
              ))}
            </div>
            </LayoutGroup>
            </motion.div>
          )}
        </>
      )}

      {/* Footer kommt app-weit aus Layout (<AppFooter/>, Jahr dynamisch) */}
      {mayEdit && (
        <Fab onClick={() => { setEditing(null); setFormOpen(true) }} label="Neues Template" />
      )}

      {copying && (
        <CopyModal template={copying} onClose={() => setCopying(null)} onCopied={bumpUsage} />
      )}
      {speaking && (
        <SpeakingCardDialog template={speaking} onClose={() => setSpeaking(null)} />
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
    </MotionConfig>
  )
}
