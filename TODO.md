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

**Offen — Paket 2 / Features (nicht kritisch):**
- **B1** GitHub-Commit-N+1 (`pdf_service._fetch_github_commits`): 1 Detail-Call pro Commit → droppen/batchen + Cache pro (repo,sha).
- **B5** nicht-sargbare `func.extract()`-Datumsfilter (Dashboard/Kunden) → halb-offene Ranges.
- **C1** Smarter KI-Import (GitHub-Commits → gruppierte Leistungsbeschreibung).
- **C2** Auto-Recurring-Rechnungen im Cron (pro Nutzer gescopt).
- **C3** Per-User-2FA-Aktivierung über die UI (`users.totp_secret` + `/auth/2fa/setup` existieren).
- **C4** Pro-Nutzer-Rechnungspräfix (koppelt an A1).
- `document_templates` global geteilt (Legal-Boilerplate); `compliance_required` globale Policy — falls je gewünscht: pro-User-Pflichtset.
