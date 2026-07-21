# Frontend-Kanon: Material 3 Expressive (celox ops)

Verbindliche Referenz für ALLE Frontend-Arbeit in diesem Repo. Bei bewusster
Abweichung: diese Datei im selben Task aktualisieren — Doku und Code driften nie.

## Projektentscheidungen

- **Scheme:** Expressive (ein Grund-Scheme; Standard-Tokens nur punktuell für
  utilitaristische Teile wie Tabellen-Hover).
- **Seed-Color:** celox blue (`--md-primary #7cb0ff`, dark tonal palette in
  `src/index.css`). Farbe NUR über Roles (`--md-*` / Tailwind-Semantik), nie Hex
  in Komponenten.
- **Dark-only (bewusste Abweichung):** internes Single-User-Tool, dunkel by
  design — kein Light-Theme gepflegt.
- **KEINE View Transitions API (bewusste Abweichung):** VT snapshottet die
  async-ladenden Chart.js-Views → Flicker/Jank. Stattdessen GPU-only Page-Reveal
  (`.page-enter`, `utils/transitions.ts::useAppNavigate` mit `data-nav`-Richtung).
  Shared-Element-Transitions daher nicht via VT; Framer Motion bewusst nicht als
  Dependency eingeführt.

## Tokens = Single Source of Truth

`frontend/src/index.css` (`:root`) + `tailwind.config.ts`. **Keine Magic Numbers**
in Komponenten — Radius/Motion/Farbe/Elevation referenzieren immer Tokens.

**Motion-Matrix (M3E, Spring→cubic-bezier-Approximation):**
- Spatial (Position/Größe/Rotation/Shape, darf overshooten):
  `--m3-spatial-{fast,default,slow}` + `-dur` (350/500/650 ms)
- Effects (Farbe/Opacity, NIE bouncen): `--m3-effect-{fast,default,slow}` + `-dur`
  (150/200/300 ms)
- Standard-Scheme ruhig: `--m3-std-spatial-fast` (300 ms)
- Speed nach Größe: klein (Switch/Chip/Badge)→fast · Fullscreen/Reveal→slow · Rest→default.
- Legacy-Aliase (`--md-ease-spring`→spatial-default, `--md-dur-short`→effect-default-dur,
  `--md-dur-medium`≈spatial-fast-dur, `--md-dur-long`→spatial-default-dur) tragen den
  Bestand; **neue Komponenten nutzen direkt `--m3-*`**.
- Farbe/Opacity → Effects-Token; Bewegung/Größe → Spatial-Token. Nie vertauschen.
- Bounce gezielt (Hero, Bestätigung), nicht flächendeckend.

**Shapes:** Scale `--md-shape-{xs..xl,full}` (8/12/16/24/28/999). Tailwind:
`rounded-card` (16) für Karten, **`rounded-dialog` (28) für ALLE Modals**,
`rounded-full` Pills. Shape-Morph on press (Buttons pill→squircle, FAB) besteht.
Hero-Spannung: `.shape-hero` (asymmetrisch 28/8/28/8) — sparsam, lenkt aufs Hero.

**Typo:** Inter als **Variable Font** (`opsz`+`wght`, index.html). Emphasized-Set:
`.md-display` (750, −0.02em, opsz 32 — Seitentitel/PageHeader) und
`.md-title-emph` (680, opsz 24 — KPI-/Hero-Zahlen). Sentence case überall,
keine Uppercase-Micro-Labels.

## Pflicht-Komponenten (kein natives Äquivalent verwenden)

- **Dropdown = `components/Select.tsx`, NIEMALS `<select>`.** Ein natives Select
  öffnet das OS-Popup und ignoriert Theme/Radien/Motion — im dunklen Theme wirkt
  es wie ein Fremdkörper. `Select` rendert die Liste per `createPortal` an
  `document.body` mit `position: fixed` (sonst Clipping in Modals/Sticky-Leisten,
  s. Transform-Ancestor-Regel), klappt bei wenig Platz nach oben, nutzt den
  getesteten `comboboxReducer` für die Tastatur und ist ARIA-Combobox.
  Sein `onChange` liefert bewusst ein natives-kompatibles `{target:{name,value}}`,
  damit gemeinsame `handleChange`-Handler unverändert funktionieren.
  `FormField type="select"` nutzt es intern — dort ist nichts zu tun.
  **Stand: 0 native `<select>` in `src/`; bei neuen Feldern so halten.**
- Eingabefeld mit Vorschlägen → `AutocompleteInput` (Feld-Modus `field="…"`
  zieht die Taxonomie), Mehrfachwerte → `TagInput`.
- Jedes Formularfeld braucht ein sichtbares Label (`<label htmlFor>`), auch in
  Inline-/Schnellerfassungszeilen — ein nacktes Datumsfeld ist nicht erklärbar.
  Zeilen mit Labels über `items-end` ausrichten, damit Felder und Buttons auf
  einer Grundlinie sitzen.
- Icon-Buttons in Listenzeilen: gleiche Trefferfläche für alle
  (`w-11 h-11 sm:w-8 sm:h-8`, `grid place-items-center`, `md-state`) und in
  EINEN Flex-Container gruppieren — sonst hängen sie auf verschiedenen Höhen.
- `:root { color-scheme: dark }` ist gesetzt: native Widgets (Datums-Picker,
  Kalender-Icon, Autofill) rendern dunkel. Nicht entfernen.

## Benannte Hero-Momente (max. 3, bewusst gestaltet)

1. **„Erledigt“** (Rainmaker Heute-Queue): `.rm-complete-exit` (Anticipation-Dip →
   Exit) + `.rm-ring-pop` am Fortschrittsring.
2. **„Bezahlt!“** (Rechnung → Status bezahlt zur Laufzeit): `StatusBadge` feiert mit
   `.paid-pop` (Spatial-Spring-Pop mit Overshoot + Erfolgs-Glow als Effects-Token).
   Initial-Render poppt nie.
3. **Page-Reveal** (`.page-enter`, richtungsbewusst fwd/back): der Standard-Übergang
   der App — Ersatz für VT (s. o.).

## A11y — hartes Gate

`prefers-reduced-motion` killt global alle Animationen/Transitions (index.css,
Ende) — jedes neue Feature muss darunter funktionieren (nie `animation-fill`
-abhängige Sichtbarkeit, siehe `animate-modal-in`-Kommentar). Fokus-Ring
(`:focus-visible`), Touch-Targets ≥44 px mobil, Kontrast AA, Modals via
`createPortal` (Transform-Ancestor-Regel in CLAUDE.md).

## Footer-Regel

App-weiter Footer kommt aus `components/AppFooter.tsx` (Layout, `<main>`-Ende):
`© {new Date().getFullYear()} Martin Pfeffer | celox.io` — Jahr IMMER dynamisch,
keine Page-eigenen Footer duplizieren.

## Bei jedem Lauf

Diese Rule + Tokens zuerst lesen. Neue Komponenten referenzieren nur Tokens.
App-Shell-Änderung (index.html) ⇒ SW-`CACHE_VERSION` bumpen (aktuell v9).
Motion-Inventar: `frontend/MOTION.md`.
