-- Zahlungsgeschwindigkeit: Datum, an dem die Rechnung als bezahlt markiert wurde.
-- Auf bestehenden DBs manuell einspielen (create_all backfillt keine Spalten):
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops -f /path/to/add_invoice_paid_at.sql
-- bzw.:
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < backend/scripts/add_invoice_paid_at.sql

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_at DATE;

-- Bestand: bezahlte Rechnungen → updated_at in der Geschäftszeitzone als Näherung
-- (historisch kein paid_at; ab jetzt wird der Wert beim Statuswechsel gesetzt).
UPDATE invoices
   SET paid_at = (timezone('Europe/Berlin', updated_at))::date
 WHERE status = 'bezahlt'
   AND paid_at IS NULL
   AND COALESCE(is_credit_note, false) = false;
