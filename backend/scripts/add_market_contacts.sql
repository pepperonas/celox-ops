-- Marktradar: Kontaktdaten je Eintrag (2026-07-30)
--
-- Der Katalog liefert diese Felder nicht — sie werden von der Herstellerseite
-- geholt (services/market_contacts.py, deterministisch, mit Beleg je Fund).
-- Alle Spalten sind OPS-Felder: `market_import._OPS_FELDER` schützt sie, ein
-- Katalog-Import darf die Anreicherung nicht löschen.
--
-- VOR dem Deploy einspielen (create_all zieht neue Spalten nicht nach).

ALTER TABLE market_products ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS email_status VARCHAR(20);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS phone VARCHAR(60);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS decision_maker VARCHAR(255);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS employee_count INTEGER;
-- Beleg je Feld: {"email": {"quelle": "<url>", "zitat": "…"}, …}
-- Ohne Beleg ist „korrekt" keine überprüfbare Aussage.
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS contact_evidence JSON;
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS contact_checked_at TIMESTAMPTZ;
