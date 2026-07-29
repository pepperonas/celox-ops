-- Karten-Farbe + eine Reihenfolge JE KANAL für die Akquise-Vorlagen (2026-07-29).
-- VOR dem Deploy einspielen (die Modellspalte ohne DB-Spalte bricht jedes SELECT).
--
-- Teil 2 ist der wichtige: `sort_order` war bisher pro (Kanal, Rubrik) von 0
-- durchnummeriert — es gibt also massenhaft gleiche Werte. Sortiert man neu nach
-- `sort_order, title`, wäre die Liste ohne Umnummerierung durcheinander.
-- Das Fenster nummeriert je Owner und Kanal in GENAU der Reihenfolge neu, in der
-- die Vorlagen bisher angezeigt wurden (category, sort_order, title) — die
-- Anordnung bleibt also sichtbar dieselbe, nur eindeutig.

BEGIN;

ALTER TABLE outreach_templates
  ADD COLUMN IF NOT EXISTS color varchar(20);

WITH neu AS (
  SELECT id,
         row_number() OVER (
           PARTITION BY owner_id, channel
           ORDER BY category, sort_order, title
         ) - 1 AS rn
  FROM outreach_templates
)
UPDATE outreach_templates t
   SET sort_order = neu.rn
  FROM neu
 WHERE neu.id = t.id
   AND t.sort_order <> neu.rn;

COMMIT;
