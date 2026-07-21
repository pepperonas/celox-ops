-- Lead-Firmendaten: Mitarbeiterzahl + Entscheider (Geschäftsführung).
-- Auf bestehenden DBs manuell einspielen VOR dem Deploy — Modellspalten ohne
-- DB-Spalten brechen alle rainmaker_leads-SELECTs:
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops \
--     -c "ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS employee_count INTEGER;" \
--     -c "ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS decision_maker VARCHAR(255);"

ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS employee_count INTEGER;
ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS decision_maker VARCHAR(255);
