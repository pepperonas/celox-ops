# MOTION.md — Motion-Inventar celox ops

Kanon: `.claude/rules/frontend-m3e.md`. Tokens: `src/index.css`.

## Token-Matrix (welcher Spring wofür)

| Token | Einsatz |
|---|---|
| `--m3-spatial-fast` (350 ms) | kleine Elemente: Button-/FAB-Press, Chips, Badge-Pop |
| `--m3-spatial-default` (500 ms) | Karten-Transform, Badge-Morph „Bezahlt!“, Dialog-Scale |
| `--m3-spatial-slow` (650 ms) | Fullscreen/große Flächen (reserviert) |
| `--m3-effect-fast/default/slow` | Farbe, Opacity, State-Layer, Glow — nie Bounce |
| `--m3-std-spatial-fast` | ruhige utilitaristische Bewegung (Tabellen-Hover) |
| `--md-ease-soft` + `--md-dur-reveal` (460 ms) | Page-/Content-Reveal (Signature-Glide) |

## Transitions & Effekte

- **Page-Reveal** `.page-enter` → `page-in-fwd`/`page-in-back` (richtungsbewusst via
  `html[data-nav]`, `useAppNavigate`). BEWUSST kein View-Transitions-API (Chart.js-
  Async-Flicker). Auf POP (`html[data-pop="1"]`) keine Entrance-Replays.
- **Entrances:** `animate-md-enter/scale/fade/pop`, `.md-stagger` (40-ms-Kaskade,
  unter `.page-enter` deaktiviert — eine Entrance genügt).
- **State-Layers:** `.md-state`, `.btn-*::after`, Hover/Active-Opacity via Effects.
- **Shape-Morph:** `.btn-primary:active` pill→squircle, `.fab:active` squircle→runder.
- **TiltCard** (Dashboard-KPIs): cursor-reaktiv, nur `(hover:hover) and (pointer:fine)`.

## Hero-Momente

1. **„Erledigt“** — `.rm-complete-exit` (Anticipation → Exit) + `.rm-ring-pop`
   (Rainmaker Today).
2. **„Bezahlt!“** — `.paid-pop` in `StatusBadge` (nur bei Laufzeit-Wechsel auf
   `bezahlt`; spatial-default-Pop + effect-slow-Glow).
3. **Page-Reveal** — s. o., der Grundpuls der App.

## Reduced Motion

`@media (prefers-reduced-motion: reduce)` (index.css-Ende) setzt alle
animation/transition-durations auf ~0 und neutralisiert Tilt. Neue Animationen
dürfen Sichtbarkeit nie von einem gelaufenen Keyframe abhängig machen.

## Pilot: Bibliotheks-Animationen auf der Vorlagen-Seite (2026-07-29)

Kanon und Arbeitsteilung: `.claude/rules/frontend-m3e.md`. JS-Token:
`src/utils/motionTokens.ts` (Drift-Wächter: `scripts/check-motion-tokens.mjs`,
läuft als `pretest`).

| Bewegung | Bibliothek | Warum dort |
|---|---|---|
| Umsortieren (Kanal + Favoriten) | motion `layout` + `LayoutGroup` | Layout-Messung; ersetzt handgeschriebenes FLIP |
| Filterwechsel | keyed `motion.div`, nur Deckkraft | s. „Ein Filterwechsel ist ein Schnitt" |
| Karte auf-/zuklappen | motion, Höhe 0 ↔ auto | hängt an React-Zustand |
| Favoriten-Sektion auf-/zuklappen | motion, Höhe 0 ↔ auto | dito |
| Kopier-Bestätigung (Knopf zeigt kurz „Kopiert") | motion `AnimatePresence` `mode="wait"` | hängt an React-Zustand |
| Stern-Puls beim Favorisieren | anime.js | ereignisgesteuerter Einmal-Effekt |

Bewusst NICHT gebaut: Chip-Häkchen, die sich zeichnen (man klickt sie im
Sekundentakt), Karten, die beim Scrollen einfliegen, und ein Umsortieren, dessen
Gleiten man abwarten muss. Der Stern pulst nur beim SETZEN — eine Belohnung fürs
Wegnehmen wäre eine widersprüchliche Rückmeldung.

### Ein Filterwechsel ist ein Schnitt, kein Umzug

Der erste Entwurf ließ `layout` über den Filterwechsel hinweg laufen und
staffelte den Eintritt. Beides war falsch, und beides fiel erst beim Zusehen auf:

- Karten, die in beiden Filtern vorkommen, behalten ihren `key`. motion hat also
  eine „vorherige Position" gemessen — oft weit unten in einer 42er-Liste,
  außerhalb des Bildes — und ist quer über die Seite dorthin geglitten.
- Bei 42 Karten kam die letzte durch die Staffelung knapp 800 ms nach dem Klick.
  Das ist Warten, nicht Rückmeldung.
- Und wer weit unten stand, landete nach dem Filtern am **Ende** der neuen Liste.

Jetzt: ein `key` aus Kanal + Rubrik tauscht den Teilbaum aus (keine vorherige
Position ⇒ kein Flug), es bewegt sich nur die Deckkraft (200 ms, Effects-Token),
und der Wechsel holt die Filterleiste mit `scrollIntoView({ block: 'nearest' })`
zurück in den Blick. `nearest` ist der Punkt: Ist die Leiste schon sichtbar,
passiert nichts. Kein `smooth` — animiertes Scrollen arbeitet gegen die
einblendende Liste (dieselbe Lehre wie beim FLIP der To-do-Liste).

Innerhalb **eines** Filters bleibt der Key gleich, dort gleiten die Karten beim
Ziehen und bei den Pfeilen weiter.

Nachgemessen (Prüfstand mit der echten Karte, 60 → 30 Karten, Chrome):

| | vorher | nachher |
|---|---|---|
| Kartenwanderung beim Filtern | quer über die Seite | 0 px, Position über alle 700 ms konstant |
| letzte Karte sichtbar | ~780 ms | 200 ms (alle gleichzeitig) |
| `scrollTop` nach dem Filtern (vorher 2207, neues Maximum 712) | 712 = Ende der neuen Liste | 20 = Anfang |
| Filtern, während die Leiste sichtbar ist (8) | — | 8, kein Sprung |

Kosten der Bibliotheken: Der Vorlagen-Chunk wuchs 11,18 → 67,54 kB gzip. Das
Startbündel bleibt bei 101 kB, weil die Seite `React.lazy` ist — beim Ausrollen
auf die ganze App wären es +56 kB im gemeinsamen Bündel.

Nebenbefund, gegen die Erwartung: Die Höhe der Favoriten-Sektion animiert mit 350
ms, die Karten darunter rutschen mit dem 500-ms-Token nach — trotzdem endet beides
9 ms auseinander (392 vs. 383 ms gemessen), weil motion die Layout-Projektion
laufend nachzieht. Also kein Nachlaufen, also keine Änderung.
