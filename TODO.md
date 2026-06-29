# TODO

Offene, bewusst zurückgestellte Arbeiten an celox ops.

## Sicherheit / Architektur

### [HIGH] Multi-User-Fähigkeit + Autorisierung (Ownership-Checks) nachholen
**Status:** zurückgestellt (App ist aktuell bewusst **Single-User**).
**Aufgedeckt durch:** automatisches Security-Review (IDOR-Hinweis auf
`GET /api/invoices/usage-period-start`, 2026-06).

**Warum aktuell unkritisch:** Es gibt genau einen authentifizierten Admin
(JWT, kein `users`-Table, kein `owner_id`/`tenant_id` an den Models). Alle
Router liegen hinter `Depends(get_current_user)`. Es existiert keine Mandanten-
grenze, die per `customer_id`/`invoice_id` überschritten werden könnte — der
IDOR-Hinweis greift daher heute nicht.

**Was zu tun ist, sobald mehr als ein Nutzer/Mandant existieren soll:**
- Datenmodell: `users`-Tabelle + `owner_id`/`tenant_id` (FK) an allen
  besitzbaren Entitäten (`customers`, `orders`, `contracts`, `invoices`,
  `leads`, `time_entries`, `expenses`, `attachments`, `document_templates`,
  `compliance_records`, `rainmaker_*`, `pagespeed_results`, `app_settings`).
- **App-weite** Autorisierung: jede Query muss auf den aktuellen Nutzer/Mandanten
  scopen (z. B. Helper `owned(query, current_user)` oder Row-Level-Filter), nicht
  nur einzelne Endpoints. Direkte `db.get(Model, id)`-Zugriffe absichern
  (Ownership prüfen → sonst 404/403).
- Betroffen u. a. (gleiches Muster wie überall): `routers/invoices.py`
  (`usage-period-start`, `get_invoice`, `generate-pdf`, …), `customers`,
  `compliance`, `attachments`, `documents`, `token_tracker`.
- Auth: Login/Registrierung mehrbenutzerfähig, Rollen (Admin/User), ggf.
  pro-Nutzer-2FA. JWT `sub` → echte User-ID statt fixem Admin-Namen.
- Migration der Bestandsdaten auf den initialen Owner.
- Tests: Cross-Tenant-Zugriffe müssen 404/403 liefern.

> Dies ist ein eigenständiges, größeres Vorhaben — punktuelle Checks an
> Einzel-Endpoints wären inkonsistent und trügerisch, daher app-weit angehen.
