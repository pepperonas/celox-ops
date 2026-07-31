-- Forum-/Community-Lückenanalyse am Marktradar-Produkt.
--   docker exec -i celox-ops-db-1 psql -U celoxops -d celoxops < backend/scripts/add_market_gap_research.sql

ALTER TABLE market_products ADD COLUMN IF NOT EXISTS forum_pains JSONB;
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS vendor_gaps JSONB;
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS remedies JSONB;
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS gap_researched_at TIMESTAMPTZ;
