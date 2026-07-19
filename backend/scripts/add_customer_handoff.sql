-- Customer-Handoff (portal/datenschutz) — Kontrakt §6.4 + fachliches Audit-Detail.
-- Auf bestehenden DBs manuell einspielen (create_all backfillt keine Spalten):
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops -f - < backend/scripts/add_customer_handoff.sql
-- bzw. via -c mit den einzelnen Statements.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS portal_handoff TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS datenschutz_handoff TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS detail TEXT;
