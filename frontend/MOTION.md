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
