-- KI-Lead-Suche: Lauf-Protokoll (Kosten/Budget) + Settings-Spalten.
-- Additiv/idempotent. Vor dem Code-Deploy einspielen (rückwärtskompatibel).

CREATE TABLE IF NOT EXISTS ai_lead_runs (
    id                  uuid PRIMARY KEY,
    owner_id            uuid REFERENCES users(id) ON DELETE CASCADE,
    brief               text        NOT NULL,
    model               varchar(40) NOT NULL,
    used_web_search     boolean     NOT NULL DEFAULT false,
    input_tokens        integer     NOT NULL DEFAULT 0,
    output_tokens       integer     NOT NULL DEFAULT 0,
    cache_write_tokens  integer     NOT NULL DEFAULT 0,
    cache_read_tokens   integer     NOT NULL DEFAULT 0,
    web_searches        integer     NOT NULL DEFAULT 0,
    cost_usd            numeric(10,4) NOT NULL DEFAULT 0,
    cost_eur            numeric(10,4) NOT NULL DEFAULT 0,
    candidates_found    integer     NOT NULL DEFAULT 0,
    leads_imported      integer     NOT NULL DEFAULT 0,
    status              varchar(20) NOT NULL DEFAULT 'ok',
    error               text,
    created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ai_lead_runs_owner_id ON ai_lead_runs (owner_id);
CREATE INDEX IF NOT EXISTS ix_ai_lead_runs_created_at ON ai_lead_runs (created_at);

ALTER TABLE app_settings
    ADD COLUMN IF NOT EXISTS ai_model varchar(40) NOT NULL DEFAULT 'claude-sonnet-5';
ALTER TABLE app_settings
    ADD COLUMN IF NOT EXISTS ai_monthly_budget_eur numeric(10,2) NOT NULL DEFAULT 20;
