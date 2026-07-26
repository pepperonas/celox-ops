-- Website-Analyse (A1): denormalisierte Zusammenfassung am Lead für die Liste.
-- VOR dem Deploy einspielen (Modellspalten ohne DB-Spalten brechen Lead-SELECTs).
-- Die Detail-/Historien-Tabelle lead_website_analyses legt create_all automatisch an.
ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS web_score INTEGER;
ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS web_rating VARCHAR(10);
ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS web_has_critical BOOLEAN;
ALTER TABLE rainmaker_leads ADD COLUMN IF NOT EXISTS web_analyzed_at TIMESTAMPTZ;
