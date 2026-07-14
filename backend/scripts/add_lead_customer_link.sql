-- Verknüpfung Pipeline-Lead → Kunde (Lead→Kunde-Konvertierung). Additiv, nullable.
-- Vor dem Code-Deploy einspielen (rückwärtskompatibel).
ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS customer_id uuid REFERENCES customers(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_rainmaker_leads_customer_id ON rainmaker_leads (customer_id);
