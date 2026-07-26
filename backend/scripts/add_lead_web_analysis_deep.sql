-- Tiefenanalyse (A2): KI-Qualitätsbewertung + PageSpeed pro Analyse-Lauf.
-- VOR dem Deploy einspielen (Modellspalten ohne DB-Spalten brechen die SELECTs).
ALTER TABLE lead_website_analyses ADD COLUMN IF NOT EXISTS ai_review JSON;
ALTER TABLE lead_website_analyses ADD COLUMN IF NOT EXISTS pagespeed JSON;
