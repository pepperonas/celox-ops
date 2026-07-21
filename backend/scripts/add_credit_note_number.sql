-- Gutschrift/Storno: Nummer der stornierten Originalrechnung denormalisiert am
-- Gutschrift-Datensatz (PDF-Pflichtangabe §14 UStG + Anzeige ohne Join).
-- Auf bestehenden DBs manuell einspielen (create_all backfillt keine Spalten):
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops \
--     -c "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS credit_note_for_number VARCHAR(20);"

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS credit_note_for_number VARCHAR(20);

-- Bestandsgutschriften nachziehen (Nummer aus dem verknüpften Original).
UPDATE invoices gs
   SET credit_note_for_number = orig.invoice_number
  FROM invoices orig
 WHERE gs.credit_note_for = orig.id
   AND gs.credit_note_for_number IS NULL;
