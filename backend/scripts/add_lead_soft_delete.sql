-- Papierkorb für Leads (Rolle „Verkäufer", 2026-07-29).
-- VOR dem Deploy des zugehörigen Codes einspielen: die Modellspalten ohne
-- DB-Spalten würden JEDEN Lead-SELECT brechen.
--
-- Zwei Teile:
--   1. Die Markierungsspalten.
--   2. Die beiden partiellen Unique-Indizes um `deleted_at IS NULL` erweitern.
--      Ohne (2) blockiert ein Lead im Papierkorb den Wiederimport derselben
--      Firma für immer — mit einer Fehlermeldung über einen Datensatz, den der
--      Nutzer nirgends sieht. Die Normalisierung selbst bleibt unverändert
--      (muss weiter mit services/lead_dedup.py übereinstimmen).
--
-- Läuft in EINER Transaktion: Postgres-DDL ist transaktional, der Unique-Schutz
-- ist für andere Sitzungen also zu keinem Zeitpunkt abwesend.

BEGIN;

ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS deleted_by_id uuid REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_rainmaker_leads_deleted_at
  ON rainmaker_leads (deleted_at);

DROP INDEX IF EXISTS uq_rainmaker_lead_owner_email;
CREATE UNIQUE INDEX uq_rainmaker_lead_owner_email
  ON rainmaker_leads (owner_id, email_norm)
  WHERE email_norm IS NOT NULL AND deleted_at IS NULL;

DROP INDEX IF EXISTS uq_rainmaker_lead_owner_website;
CREATE UNIQUE INDEX uq_rainmaker_lead_owner_website
  ON rainmaker_leads (owner_id, website_norm)
  WHERE website_norm IS NOT NULL AND deleted_at IS NULL;

COMMIT;
