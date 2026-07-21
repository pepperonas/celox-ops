-- Lead-„Target" (Pitch-Winkel/Pain, wie ein Tag gepflegt, eigene Achse).
-- Auf bestehenden DBs manuell einspielen VOR dem Deploy — eine Modellspalte
-- ohne DB-Spalte bricht alle rainmaker_leads-SELECTs:
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops \
--     -c "ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS target VARCHAR(120);"

ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS target VARCHAR(120);
CREATE INDEX IF NOT EXISTS idx_rainmaker_leads_target ON rainmaker_leads (target);
