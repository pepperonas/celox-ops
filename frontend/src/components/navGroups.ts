/**
 * Reine Nav-Logik (ohne React/DOM) → unit-testbar. Layout.tsx nutzt diese Helfer
 * zum Aufbau der einklappbaren Gruppen und für die „ist offen?"-Entscheidung.
 */
export interface NavItem {
  to: string
  label: string
  adminOnly?: boolean
  icon?: unknown
}

export interface NavGroupMeta {
  title: string
  paths: string[]
}

export interface NavGroup<T extends NavItem> {
  title: string
  items: T[]
}

/** Aktiv = exakt Dashboard ('/') bzw. Pfad-Präfix-Match für alle anderen. */
export function isItemActive(pathname: string, to: string): boolean {
  if (to === '/') return pathname === '/'
  return pathname === to || pathname.startsWith(to + '/')
}

/**
 * Baut aus der flachen Item-Liste + Gruppen-Metadaten die sichtbaren Gruppen
 * (Rollen-Filter angewendet, leere Gruppen entfernt) und das einzelne Dashboard.
 *
 * `allowedPaths` ist die Erlaubnisliste zugeschnittener Rollen (z. B. Verkäufer):
 * ist sie gesetzt, bleibt NUR was darin steht — inklusive des Dashboards, das
 * sonst als Einzeleintrag oben durchrutschen würde.
 */
export function buildNavGroups<T extends NavItem>(
  items: T[],
  meta: NavGroupMeta[],
  isAdmin: boolean,
  allowedPaths?: string[] | null,
): { dashboard: T | undefined; groups: NavGroup<T>[] } {
  const allow = allowedPaths ? new Set(allowedPaths) : null
  // Bei einer zugeschnittenen Rolle entscheidet AUSSCHLIESSLICH die
  // Erlaubnisliste. Sonst müsste jeder Eintrag zwei Regeln erfüllen, und
  // „Nachrichten-Vorlagen" (adminOnly) wäre für Verkäufer unsichtbar, obwohl sie
  // ihn ausdrücklich sehen sollen.
  const canSee = (i: NavItem) => (allow ? allow.has(i.to) : !i.adminOnly || isAdmin)
  const byPath = new Map(items.map((i) => [i.to, i]))
  const dashboardItem = byPath.get('/')
  const dashboard = dashboardItem && canSee(dashboardItem) ? dashboardItem : undefined
  const groups = meta
    .map((g) => ({
      title: g.title,
      items: g.paths.map((p) => byPath.get(p)).filter((i): i is T => !!i && canSee(i)),
    }))
    .filter((g) => g.items.length > 0)
  return { dashboard, groups }
}

/**
 * Eine Gruppe ist offen, wenn: die Rail als Icon-Leiste läuft (dann alle flach),
 * ODER sie nicht manuell zugeklappt ist, ODER sie die aktive Route enthält (die
 * aktive Seite bleibt immer sichtbar).
 */
export function isGroupOpen<T extends NavItem>(
  group: NavGroup<T>,
  opts: { railCollapsed: boolean; collapsedTitles: string[]; activePath: string },
): boolean {
  if (opts.railCollapsed) return true
  if (!opts.collapsedTitles.includes(group.title)) return true
  return group.items.some((i) => isItemActive(opts.activePath, i.to))
}

/** Toggle-Helfer für die Liste zugeklappter Gruppen-Titel (rein). */
export function toggleCollapsed(titles: string[], title: string): string[] {
  return titles.includes(title) ? titles.filter((t) => t !== title) : [...titles, title]
}
