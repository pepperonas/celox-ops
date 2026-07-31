-- Ausgaben: Zahlungsstand (Cash/EÜR). create_all backfillt keine Spalten.
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < backend/scripts/add_expense_paid.sql

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS paid BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS paid_at DATE;

-- Bestand: bisher alles „gebucht" → bezahlt, Zahlungsdatum = Buchungsdatum.
UPDATE expenses
   SET paid = TRUE,
       paid_at = date
 WHERE paid_at IS NULL
   AND paid IS TRUE;
