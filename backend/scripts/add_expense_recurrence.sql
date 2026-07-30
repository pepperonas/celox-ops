-- Ausgaben-Turnus (Wiederkehr-Intervall). create_all backfillt keine Spalten.
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < backend/scripts/add_expense_recurrence.sql

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS recurrence VARCHAR(20);

-- Bestand: bisher nur bool recurring → Standard monatlich.
UPDATE expenses
   SET recurrence = 'monthly'
 WHERE recurring IS TRUE
   AND recurrence IS NULL;
