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
  Shared-Element-Transitions daher nicht via VT.

## Animations-Bibliotheken: motion.dev + anime.js (seit 2026-07-29)

Die frühere Regel lautete „Framer Motion bewusst nicht als Dependency
eingeführt". Sie ist **aufgehoben** — motion.dev (= Framer Motion, umbenannt) und
anime.js sind eingeführt, zunächst als **Pilot auf der Vorlagen-Seite**
(`/akquise`). Vor einem Rollout auf die restliche App ist die Bundle-Frage unten
zu klären.

**Arbeitsteilung — verbindlich.** Beide Bibliotheken können Tweens, Springs,
Timelines und Stagger; ohne scharfe Trennung überdecken sie sich fast vollständig
und niemand weiß, womit die nächste Animation gebaut wird:

- **motion.dev** — alles, was an **React-Zustand oder Layout** hängt: `layout`
  (Umsortieren), `AnimatePresence` (Ein-/Austritt), `LayoutGroup`, `MotionConfig`.
  Ersetzt handgeschriebenes FLIP.
- **anime.js** — **ereignisgesteuerte Einmal-Effekte** auf dem DOM: Impulse
  (Stern-Puls), Zahlen-Countup, SVG-Zeichnen.

**Token statt eigener Physik.** `src/utils/motionTokens.ts` ist das JS-Pendant der
CSS-Token-Matrix; motion bekommt `duration` + `ease` daraus, NICHT motions eigene
Feder-Physik. Sonst sähe dieselbe Geste an CSS- und JS-Stellen unterschiedlich aus.
Der Grund für die Kopie: Die Web Animations API akzeptiert keine
CSS-Custom-Property als Easing (Repo-Regel, entstanden am disco-Bug).
`frontend/scripts/check-motion-tokens.mjs` läuft als `pretest` und schlägt fehl,
wenn CSS und JS auseinanderlaufen — per Mutationstest belegt. Bewusst ein Skript
und kein vitest-Test: **Vitest ersetzt CSS-Importe durch einen leeren String,
auch mit `?raw`** (nachgemessen, Länge 0) — der Test wäre still grün gewesen.

**Reduced Motion ist doppelt zu bedienen.** `<MotionConfig reducedMotion="user">`
deckt motion ab; anime.js fragt selbst über `prefersReducedMotion()`. Die
CSS-Regel am Ende von `index.css` erreicht JS-Animationen NICHT.

**Bundle (gemessen, 2026-07-29).** Der Outreach-Chunk wuchs von 11,18 auf
67,52 kB gzip (+56 kB). Das **Start-Bundle blieb unverändert** (101 kB gzip), weil
die Seite `React.lazy` ist. Bei einem Rollout in den geteilten Bundle wären es
+56 % auf die Startlast — dann sind `LazyMotion`/`m`-Komponenten oder der Verzicht
auf motions Layout-Animationen zu prüfen.

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

## Icons: eigener Satz, keine Emojis

**Regel: In der Oberfläche steht kein Emoji.** Emojis sind Schrift, keine Icons —
sie kommen in der Systemfarbe (ignorieren also jedes Theme-Token), sehen auf macOS,
Windows und Android unterschiedlich aus, tragen keine Strichbreite und kein Raster,
und der Screenreader liest ihren Unicode-Namen („Bündel Geldscheine") statt der
Bedeutung in dieser App. Dasselbe gilt für schriftabhängige Glyphen, die als Icon
missbraucht werden: `▲ ▼ ▸ ▾ ▶ ⓘ ℹ ◷`.

**Der Satz** liegt in `src/components/icons/catalog.ts` (Icons als **Daten**),
benutzt wird er über `<Icon name="…" />`. Gezeichnet ist er auf dem
Material-Raster — recherchiert, nicht geschätzt:

- **24×24 mit 2 dp Rand**, also **Live-Area 20×20** (Koordinaten 2…22).
- **2 dp Strichbreite** überall — Kurven, Winkel, innen wie außen. `Icon` skaliert
  sie mit der Größe (Näherung der `opsz`-Achse), damit ein Icon bei 16 px nicht
  fett und bei 40 px nicht dünn wirkt.
- Keylines Kreis ⌀20 · Quadrat 18×18 · Rechteck 20×16 / 16×20 — daran orientieren
  sich die Grundformen, damit alle Icons **optisch** gleich groß wirken.
- **Runde Enden und Verbindungen** (`round`): bewusste Wahl fürs Expressive-Scheme,
  das durchgehend große Radien nutzt. Scharfe Enden wirkten daneben fremd.
- **Farbe immer `currentColor`** — das Icon erbt die Textfarbe seines Kontextes und
  funktioniert damit in jedem Token.
- **Zustand über die Füllung** (MD3-`fill`-Achse): `<Icon name="star" filled={…} />`
  nutzt die `solid`-Fassung. Nur Farbe wäre der schwächere Zustandswechsel.

**Neues Icon anlegen:** in `catalog.ts` eintragen (Live-Area einhalten), dann
`<Icon name="…" />`. **Kein `A`-Bogen in Pfaden** — bei einem Bogen liegt der
Scheitel nicht in den Koordinaten, damit wäre die Rasterprüfung keine echte
Schranke; Bézier-Kurven liegen garantiert in der Hülle ihrer Kontrollpunkte. Runde
Ecken kommen über `rx` am Rechteck.

**Zwei Tests halten das:** `catalog.test.ts` rechnet für jedes Icon nach, dass es in
der Live-Area liegt, sie ausnutzt, ungefähr zentriert ist und keinen Bogen benutzt;
`noEmoji.test.ts` durchsucht `src/` (über `import.meta.glob`, damit kein
`@types/node` nötig ist) nach Bildzeichen.

**Bewusst erlaubt bleiben:**
- Typografische Zeichen **im Satz**: `→ ↑ ↓ ✓ ✕ · …`. Im Fließtext sind das
  Schriftzeichen; ein SVG dazwischen bräche die Grundlinie. Als eigenständige
  Schaltfläche werden sie trotzdem Icons.
- `⌘` als Tastensymbol, `−` als Minuszeichen, `•` als Aufzählungspunkt.
- Emojis in **Kommentaren** (dokumentieren, welches Emoji ein Icon ersetzt hat) und
  in **Testfixtures** (`clipboard.test.ts` prüft mit ihnen Unicode-Grenzen).

**Wo kein SVG stehen kann**, entfällt das Zeichen ersatzlos: `title`-Attribute,
Toast-**Texte** und Dropdown-Option-Labels sind Strings. Ein Toast-**Icon** dagegen
nimmt einen ReactNode: `toast('…', { icon: <Icon name="warning" size={18} /> })`.

**Barrierefreiheit:** `Icon` setzt standardmäßig `aria-hidden` — ein Icon neben Text
darf nicht doppelt vorgelesen werden. Ist das Icon die **einzige** Information
(Icon-Button), braucht der Knopf ein `aria-label`/`title`; alternativ `label` am
Icon. Beim Ersetzen eines Emojis prüfen, ob dessen Bedeutung vorher der einzige
Hinweis war — sonst verschlechtert der Umbau die Zugänglichkeit.

## Pflicht-Komponenten (kein natives Äquivalent verwenden)

- **Icon = `components/Icon.tsx`** mit einem Namen aus `icons/catalog.ts` — **nie ein Emoji** (Begründung und Raster oben).
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
