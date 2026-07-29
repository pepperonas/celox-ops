-- Eigene Reihenfolge innerhalb der Favoriten-Sektion (2026-07-29).
-- VOR dem Deploy einspielen (Modellspalte ohne DB-Spalte bricht jedes SELECT).
--
-- Warum eine zweite Spalte und nicht `sort_order`: Die Favoriten-Sektion ist
-- kanalübergreifend, `sort_order` zählt aber je Kanal ab 0. Eine Telefonvorlage
-- mit 0 und eine E-Mail mit 0 stünden dort willkürlich nebeneinander — und ein Zug
-- in den Favoriten würde die Kanal-Reihenfolge mitverändern.
--
-- Bewusst NULL-fähig und ohne Vorbelegung: NULL heißt „noch nicht einsortiert" und
-- sortiert hinten. Ein neuer Stern hängt sich damit an, statt eine bestehende
-- Anordnung zu durchmischen. Solange nie gezogen wurde, sind alle NULL und die
-- Sektion sortiert nach Titel — vorhersagbar, im Gegensatz zu heute.

ALTER TABLE outreach_templates
  ADD COLUMN IF NOT EXISTS favorite_order integer;
