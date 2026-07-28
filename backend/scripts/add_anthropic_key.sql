-- Anthropic-API-Key pro Arbeitsbereich (jeder Inhaber rechnet über seinen eigenen ab).
-- VOR dem Deploy einspielen: eine Modellspalte ohne DB-Spalte bricht jedes SELECT
-- auf app_settings (und damit Rechnungsnummern, KI-Budget, Places-Key).
--
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < add_anthropic_key.sql
--
ALTER TABLE app_settings
    ADD COLUMN IF NOT EXISTS anthropic_api_key varchar(255);
