-- Referenzkunden: Kontaktdaten je Firma (2026-07-30)
--
-- Gleiche Struktur wie bei den Herstellern (market_products): Werte plus Beleg je
-- Feld in `contact_evidence`. Die Website kommt hier meist NICHT von der Logo-Wand,
-- sondern aus einer Namensauflösung über Google Places — deshalb trägt der Beleg
-- zusätzlich die Herkunft ("places" vs. "verlinkt").
--
-- VOR dem Deploy einspielen (create_all zieht neue Spalten nicht nach; die Tabelle
-- existiert in Prod bereits mit 3.712 Zeilen).

ALTER TABLE market_references ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS email_status VARCHAR(20);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS phone VARCHAR(60);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS decision_maker VARCHAR(255);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS employee_count INTEGER;
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS address VARCHAR(255);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS website_source VARCHAR(20);
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS contact_evidence JSON;
ALTER TABLE market_references ADD COLUMN IF NOT EXISTS contact_checked_at TIMESTAMPTZ;
