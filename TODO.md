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

**Optionale Folge-Verbesserungen (nicht kritisch):**
- Per-User-2FA-Aktivierung über die UI (Secret persistieren; Backend-Spalte
  `users.totp_secret` existiert bereits, `/auth/2fa/setup` liefert QR/Secret).
- Cron (`run_cron`) läuft unscoped/global — Rainmaker-Reminder pro Nutzer
  iterieren, sobald mehrere aktive Nutzer existieren.
- `document_templates` sind global geteilt (Legal-Boilerplate); `compliance_required`
  ist eine globale Policy. Falls je gewünscht: pro-User-Pflichtset.
- Backup-Export (`/api/backup/export`, jetzt admin-only) scoped Owned-Tabellen auf
  den aufrufenden Admin; ein echtes Voll-DB-Backup ist weiterhin `scripts/backup.sh`.
