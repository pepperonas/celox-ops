import type { DuplicateGroup } from '../../types'

export interface GroupSel {
  included: boolean
  keeperId: string
  dupIds: string[]        // gewählte Duplikate (ohne Keeper)
}

export interface BatchMerge { keeper_id: string; duplicate_ids: string[] }

export interface BatchSummary {
  merges: BatchMerge[]
  groupCount: number
  deleteCount: number      // Leads, die gelöscht werden
  activityCount: number    // Aktivitäten, die auf Keeper wandern
  colleagueCount: number   // enthaltene „Kollegen"/Fuzzy-Gruppen (Warnung)
  overlaps: boolean        // ein Lead in mehreren Gruppen (würde übersprungen)
}

const LOW_CONFIDENCE = new Set(['colleagues', 'fuzzy'])

/** Baut Batch-Plan + Warnzähler aus den ausgewählten Gruppen (rein/testbar). */
export function buildBatchSummary(
  groups: DuplicateGroup[], sel: Record<number, GroupSel>,
): BatchSummary {
  const merges: BatchMerge[] = []
  let deleteCount = 0, activityCount = 0, colleagueCount = 0, overlaps = false
  const seen = new Set<string>()

  groups.forEach((g, i) => {
    const s = sel[i]
    if (!s || !s.included) return
    const dupIds = s.dupIds.filter((id) => id !== s.keeperId)
    if (dupIds.length === 0) return
    merges.push({ keeper_id: s.keeperId, duplicate_ids: dupIds })
    deleteCount += dupIds.length
    for (const m of g.members) if (dupIds.includes(m.id)) activityCount += m.activity_count
    if (LOW_CONFIDENCE.has(g.reason)) colleagueCount++
    for (const id of [s.keeperId, ...dupIds]) {
      if (seen.has(id)) overlaps = true
      seen.add(id)
    }
  })

  return { merges, groupCount: merges.length, deleteCount, activityCount, colleagueCount, overlaps }
}
