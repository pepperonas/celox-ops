-- Herkunftsschlüssel für importierte Ausgaben (Hostinger u. a.) + Idempotenz.
-- VOR dem Deploy einspielen: eine Modellspalte ohne DB-Spalte bricht jedes
-- SELECT auf expenses (Ausgabenliste, EÜR, Dashboard).
--
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < add_expense_external_ref.sql
--
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS external_ref varchar(120);
CREATE INDEX IF NOT EXISTS ix_expenses_external_ref ON expenses (external_ref);
-- Pro Arbeitsbereich nur einmal derselbe Herkunftsschlüssel; partiell, damit
-- handgepflegte Ausgaben (external_ref NULL) unbegrenzt erlaubt bleiben.
CREATE UNIQUE INDEX IF NOT EXISTS uq_expense_owner_external_ref
    ON expenses (owner_id, external_ref) WHERE external_ref IS NOT NULL;
