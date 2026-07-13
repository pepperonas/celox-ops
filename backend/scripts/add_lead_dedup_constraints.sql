-- Duplikat-Absicherung für rainmaker_leads (idempotent, race-sicher).
-- Generierte, normalisierte Dedup-Spalten + partielle Unique-Indizes pro Owner.
-- Die Normalisierung MUSS mit services/lead_dedup.py::norm_email/norm_website
-- und models/rainmaker_lead.py übereinstimmen.
-- Ausführen VOR dem Deploy des zugehörigen Codes (rückwärtskompatibel).
-- Benötigt PostgreSQL 12+ (GENERATED … STORED).

ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS email_norm text
  GENERATED ALWAYS AS (nullif(lower(btrim(email)), '')) STORED;

ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS website_norm text
  GENERATED ALWAYS AS (
    nullif(btrim(rtrim(
      regexp_replace(regexp_replace(lower(btrim(website)), '^https?://', '', 'i'),
      '^www\.', '', 'i'), '/')), '')
  ) STORED;

CREATE UNIQUE INDEX IF NOT EXISTS uq_rainmaker_lead_owner_email
  ON rainmaker_leads (owner_id, email_norm) WHERE email_norm IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_rainmaker_lead_owner_website
  ON rainmaker_leads (owner_id, website_norm) WHERE website_norm IS NOT NULL;
