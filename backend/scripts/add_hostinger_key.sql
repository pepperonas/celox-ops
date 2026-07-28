-- Hostinger-API-Key pro Arbeitsbereich (Kostenimport VPS/Domains).
-- VOR dem Deploy einspielen: eine Modellspalte ohne DB-Spalte bricht jedes
-- SELECT auf app_settings (Rechnungsnummern, KI-Budget, Places-Key).
--
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < add_hostinger_key.sql
--
ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS hostinger_api_key varchar(255);
