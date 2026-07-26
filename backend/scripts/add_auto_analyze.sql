-- Automatische Website-Analyse nach dem Lead-Import (Workspace-Schalter).
-- VOR dem Deploy einspielen: eine Modellspalte ohne DB-Spalte bricht jedes
-- SELECT auf app_settings (und damit Rechnungsnummern, KI-Budget, Places-Key).
--
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops -f - < add_auto_analyze.sql
--
ALTER TABLE app_settings
    ADD COLUMN IF NOT EXISTS auto_analyze_websites boolean NOT NULL DEFAULT true;
