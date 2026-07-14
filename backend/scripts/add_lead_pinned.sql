-- Bookmark/Pin für Pipeline-Leads: gepinnte Leads sortieren in ihrer Spalte nach oben.
-- create_all backfillt keine Spalten auf bestehenden Tabellen → manuelles ALTER.
ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS pinned boolean NOT NULL DEFAULT false;
