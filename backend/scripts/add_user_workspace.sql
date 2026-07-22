-- Geteilter Arbeitsbereich + Rolle „mitarbeiter".
-- VOR dem Deploy einspielen (Modellspalte ohne DB-Spalte bricht alle User-SELECTs
-- und damit den Login):
--   docker exec celox-ops-db-1 psql -U celoxops -d celoxops -f - < backend/scripts/add_user_workspace.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS works_for_id UUID REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_users_works_for_id ON users (works_for_id);

-- Die Rolle ist ein VARCHAR-Enum (native_enum=False); die Spalte muss den
-- längeren Wert „mitarbeiter" fassen (vorher length=10).
ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20);
