# TODO

Offene / kürzlich erledigte Arbeiten an celox ops.

## Sicherheit / Architektur

### [DONE] Multi-User-Fähigkeit + Autorisierung (Daten-Isolation)
**Status:** ✅ umgesetzt (2026-06). Isolierte Workspaces, admin-verwaltete Konten,
Rollen admin/user.
- `users`-Tabelle + DB-gestützte Auth, `.env`-Admin als Bootstrap-User.
- `owner_id` (FK→users, CASCADE) auf allen besitzbaren Tabellen; Bestandsdaten auf
  den Admin backfilled.
- Automatischer Owner-Filter (SQLAlchemy `with_loader_criteria`) + `before_flush`-
  Stamp via Request-ContextVar (`app/tenancy.py`). Dashboard-Cache pro Owner.
- Nutzerverwaltung (`/api/users`, Admin-only) + Frontend-Seite **Benutzer** +
  Self-Service-Passwortänderung. Öffentliche Registrierung bewusst deaktiviert.
- Verifiziert: zweiter Nutzer sieht 0 Datensätze; Admin unverändert.

### [DONE] Multi-User-Härtung Paket 1 (2026-07)
- A1 Rechnungsnummer pro Owner unique (`uq_invoice_owner_number`).
- A2 iCal-Feed pro-Nutzer-Token (`users.ical_token`), Owner-gescopt (war Cross-Tenant-Leak).
- A3 Rainmaker-Reminder-Cron iteriert aktive Nutzer, ContextVar je Nutzer, Dedupe pro Owner, Mail an `user.email`.
- A4 Cross-Tenant-FK-Prüfung (invoices/activities/attachments/time-entries). A6 Backup global.
- Perf: WeasyPrint via `to_thread` (monthly-report/pagespeed), `/charts`-Cache pro Nutzer, +14 Indizes.

### [DONE] Paket 2 — Performance (2026-07)
- **B1** GitHub-Commit-Stats parallel (ThreadPool 8) + Cache pro (repo,sha) statt N+1 (1.0s kalt / 0.27s warm bei 11 Commits verifiziert).
- **B5** WHERE-Datumsfilter (Dashboard/Monatsbericht) auf halb-offene Ranges (sargbar); Zahlen unverändert verifiziert.

### [DONE] C1 — Smarter KI-Import (2026-07)
GET `/api/github/summary` (owner-gescopt) gruppiert Commit-Betreffs zu einer
Leistungsbeschreibung; KI-Import füllt `service_description` (nur wenn leer/auto,
Marker „Erbrachte Leistungen ("). Hinweis: Qualität hängt von der Commit-Message-
Hygiene ab (Repos mit „Prefix:"-Konvention → echte Themen; prosaische Commits →
gekappte Liste). LLM-Variante bewusst nicht gebaut (kein Anthropic-Key nötig).

### [DONE] C2 — Auto-Recurring-Rechnungen (2026-07)
`services/invoice_service.generate_due_recurring` (owner-gescopt, idempotent via
`last_invoiced_date`) läuft stündlich im Cron pro aktivem Nutzer; Endpoint
`/generate-recurring` nutzt dieselbe Funktion. Verifiziert: 1 Rechnung bei
Fälligkeit, 0 bei Wiederholung, korrekt owner-isoliert.

### [DONE] C4 — Pro-Nutzer-Rechnungspräfix (2026-07)
`app_settings.invoice_prefix` (Default "CO"); `generate_invoice_number` nutzt das
owner-gescopte Präfix. In Einstellungen → Rechnungen konfigurierbar. Verifiziert:
martin behält CO, Test-Nutzer bekommt eigenen Nummernkreis (ACME-2026-…).

### [DONE] C3 — Per-User-2FA-Aktivierung in der UI (2026-07)
`/auth/2fa/{init,enable,disable}` + 2FA-Karte in den Einstellungen (QR scannen +
Code bestätigen / deaktivieren). Verifiziert: Login erzwingt danach den TOTP-Code.

**Optionale Restpunkte (nicht kritisch):**
- `document_templates` global geteilt (Legal-Boilerplate); `compliance_required` globale Policy — falls je gewünscht: pro-User-Pflichtset.
