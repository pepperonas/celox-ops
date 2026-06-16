# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

celox ops is a full-stack business management webapp for freelancers/IT consultants. German-language UI. Single-user JWT auth. Manages customers, orders, contracts, invoices (with PDF generation), leads, time tracking, expenses, the **Rainmaker** acquisition-activation module, and integrates with the Claude Token Tracker for AI usage transparency. The frontend uses a **Material Design 3 Expressive** dark theme.

## Commands

### Production
```bash
docker compose up -d --build          # Build and start all services
docker compose up -d --build backend   # Rebuild backend only
docker compose up -d --build frontend  # Rebuild frontend only
docker compose restart backend         # Restart without rebuild (picks up .env changes)
docker compose down                    # Stop all
```

### Development
```bash
docker compose -f docker-compose.dev.yml up -d --build
# Backend: http://localhost:8000 (auto-reload)
# Frontend: http://localhost:5173 (Vite HMR)
# API Docs: http://localhost:8000/docs
# DB: localhost:5433
```

### Type Checking & Validation
```bash
cd frontend && npx tsc --noEmit       # TypeScript check (no lint/test setup — only tsc)
```

### Database
```bash
# Add column (tables created via Base.metadata.create_all on startup — Alembic exists but is NOT used for auto-migrations)
docker exec celox-ops-db-1 psql -U celoxops -d celoxops -c "ALTER TABLE tablename ADD COLUMN colname TYPE;"
```

### Deployment to VPS
```bash
tar czf /tmp/celox-ops.tar.gz --exclude='.git' --exclude='node_modules' --exclude='.DS_Store' --exclude='._*' --exclude='.env' --exclude='.claude' .
scp /tmp/celox-ops.tar.gz root@YOUR_VPS:/tmp/
ssh root@YOUR_VPS 'cd /opt/celox-ops && tar xzf /tmp/celox-ops.tar.gz && rm /tmp/celox-ops.tar.gz && find . -name "._*" -delete && docker compose up -d --build backend frontend && docker compose restart nginx'
```
**Important**: Always `restart nginx` after rebuilding backend/frontend — Docker assigns new container IPs and nginx caches the old DNS resolution, causing 502 errors.

## Architecture

### Backend (Python 3.12, FastAPI)
- **Entry point**: `backend/app/main.py` — FastAPI app with lifespan (creates tables + starts hourly cron)
- **Config**: `backend/app/config.py` — Pydantic Settings, all from `.env`
- **Database**: `backend/app/database.py` — async SQLAlchemy 2.0 with asyncpg, connection pooling
- **Auth**: `backend/app/auth.py` — JWT (python-jose), single-user, OAuth2PasswordBearer
- **Pattern**: Each module has model → schema → router. All routers registered in main.py after app creation (to avoid circular imports).
- **Models inherit from `Base`** defined in `models/customer.py`. New models MUST import Base from there.
- **All list endpoints return paginated**: `{items: [], total, page, page_size, pages}` — NOT plain arrays. Exception: `GET /api/attachments` returns a plain list.
- **UUIDs**: All primary keys are UUID (asyncpg uses its own UUID type — serialize with `str()` for JSON).
- **Enum values**: Stay ASCII in code (`ueberfaellig`, `gekuendigt`, `halbjaehrlich`). German umlauts only in user-facing text/labels.
- **PDF generation**: WeasyPrint + Jinja2 templates in `backend/app/templates/`. Signature loaded as base64. Footer uses `@page @bottom-center` (not position:fixed).
- **Cron**: Background asyncio task in lifespan checks overdue invoices hourly.
- **Backup export** (`routers/backup.py`): Auto-discovers all tables via `Base.registry.mappers` — no manual list needed for new tables.

### Frontend (React 18, TypeScript, TailwindCSS, Vite)
- **Entry**: `frontend/src/main.tsx` → `App.tsx` (routing) → `Layout.tsx` (sidebar + content)
- **State**: Zustand for auth (`store/authStore.ts`), localStorage for JWT
- **API client**: `api/client.ts` — Axios with JWT interceptor, 401 redirect
- **Types**: All in `frontend/src/types/index.ts` — must match backend Pydantic schemas exactly
- **Routing**: German paths (`/kunden`, `/auftraege`, `/rechnungen`, `/vorgemerkt`, `/ausgaben`, etc.)
- **Theme**: **Material Design 3 Expressive** (dark). The token layer lives in `index.css`: MD3 tonal surfaces as RGB-channel CSS vars (`--c-bg`, `--c-surface`, `--c-accent`, …) so Tailwind opacity modifiers (`bg-danger/10`) keep working; expressive shape scale, elevation (`shadow-elev-1..3`), motion tokens (easing `ease-emphasized/decelerate/spring`, durations `duration-short/medium/long`), state-layer helper `.md-state`, pill `.btn-*` with shape-morph on press, `.fab`, `.md-spinner`, keyframe utilities (`animate-md-enter/scale/pop`, `.md-stagger`, `.md-skeleton`). `tailwind.config.ts` maps the legacy semantic names (`bg`, `surface`, `accent`, …) onto these vars. Reusable MD3 components: `PageHeader`, `Fab`, `FilterChips`, `SegmentedButtons`, `LoadingIndicator` (plus restyled `StatusBadge`, `DataTable`, dialogs). Labels are sentence-case (no uppercase micro-labels). `prefers-reduced-motion` disables animations.
- **Motion / navigation craft** (`utils/transitions.ts`): in-app navigation runs through `useAppNavigate()` (drop-in for `useNavigate`), which sets a direction flag (`html[data-nav="forward"|"back"]`, pass `{ back: true }` for up-a-level) and then navigates. The incoming content reveals via a **GPU-only CSS animation** (`.page-enter` → `page-in-fwd`/`page-in-back`, opacity + transform) on a route-keyed wrapper in `Layout`. **Important:** this deliberately does NOT use the View Transitions API — VT snapshots the destination, which flickers/janks with our async-loading, Chart.js-canvas-heavy views (it captures the loading state, then hard-swaps when data/canvas arrive). The cheap reveal animates the real DOM, so async content just appears inside the fading container. `useScrollRestoration(mainRef)` remembers the `<main>` scrollTop per history entry and restores it on POP (no animated scroll); it also sets `html[data-pop="1"]` so entrance animations don't replay on back/forward. To avoid double motion, `.page-enter .md-stagger > *` is disabled (the page reveal is the single entrance). Reactive `TiltCard` (Dashboard KPIs) tilts toward the cursor, gated to `(hover:hover) and (pointer:fine)` + reduced-motion. The Rainmaker "Erledigt" moment uses `.rm-complete-exit` (queue item leaves) + `.rm-ring-pop` (progress ring). Reduced motion → instant navigation. The scroll container is `<main>`, NOT the window.
- **Charts**: Chart.js + react-chartjs-2. Cast options as `any` to avoid TS issues with Chart.js types.
- **Tab persistence**: CustomerDetail uses URL hash (`#auftraege`, `#dokumente`, `#tokens`) for tab state.

### Rainmaker (Acquisition Activation)
- **Action-first acquisition tool** — surfaces *what to do today*, not a contact list. Backend under `/api/rainmaker` (`routers/rainmaker.py`), engine helpers in `services/rainmaker_service.py`. Frontend under `/rainmaker/*` (pages in `pages/rainmaker/`), own pill sub-nav (`RainmakerNav`) + footer.
- **5 models** (`rainmaker_lead`, `rainmaker_activity`, `rainmaker_settings`, `rainmaker_streak`, `rainmaker_template`) — registered for `create_all` in `main.py`, `native_enum=False` enums, **no `owner_id`** (single-user); `settings`/`streak` are single-row tables (`get_or_create_*`).
- **Activation engine**: a lead's "next action" = earliest planned activity by `due_date`. An active lead (status not `won`/`lost`/`dormant`) without a planned activity is **"rotting"** and surfaced in red. `GET /today` returns the queue (planned, due ≤ today, sorted by priority + overdueness) + rotting list + progress.
- **Next-Action-Zwang**: `POST /activities/{id}/complete` logs done (+outcome/notes) and **atomically requires** a next planned action — unless the lead is closed (`won`/`lost`/`dormant`). Returns 400 otherwise. After mutating it reloads `lead.activities` (`refresh(..., attribute_names=["activities"])`) so the recomputed next-action isn't stale.
- **Gamification**: daily quota (settings) vs `count_done_today`; points per type (call 10 · visit 20 · email/message/follow_up 5; ×1.5 at streak ≥ 7) via `register_completion`. **Working-day streak**: only Mon–Fri count (weekends are bonus = points only, never break it); missed working days consume a monthly **freeze** budget (`rainmaker_streak.freeze_remaining`, replenished to `settings.freezes_per_month` via `_ensure_monthly_freezes`) before the streak resets. `display_streak`/`get_streak_display` compute the live value (0 if missed working days exceed remaining freezes). The `freeze_remaining`/`freeze_period`/`freezes_per_month` columns were added via `ALTER TABLE` (create_all doesn't backfill columns on existing tables).
- **Reminder**: `check_rainmaker_reminder()` runs inside the existing hourly `run_cron` loop (NOT APScheduler). Sends one mail/day at `reminder_time` via the existing `send_email` SMTP when the quota is unmet; in-memory dedupe (`_reminder_sent_on`, like `_stats_cache`). Email channel only; no-ops without SMTP.
- **Templates** (`/templates`): email/message with `{company}`/`{contact_name}`/`{role}` placeholders; LeadDetail can launch a `mailto:` from a template with placeholders substituted.
- **Acquisition goals** (`rainmaker_goal`, `/goals` CRUD + `/goals/seed` idempotent): user-defined channels (e.g. "Neukunden Telefon-Akquise", "LinkedIn anschreiben") with a `suggested_type` (pre-fills the action type when planning, overridable) and a **daily_target**. Activities optionally carry `goal_id` (column added via `ALTER`; the `rainmaker_goal` table itself is auto-created by create_all). `/today` returns per-goal `done_today/daily_target` (shown as "Tagesziele" bars) plus `total_leads`. The Heute empty-state is context-aware via `total_leads`/`done_today` (no leads → "leg den ersten an"; nothing due → "heute nichts fällig"; only truly cleared → "🎉").
- **Tests**: `backend/tests/test_rainmaker.py` — DB-free unit tests for rotting, next-action selection, streak display, points (run with the smoke tests in-container).

### Token Tracker Integration
- Backend proxies to Token Tracker via `TOKEN_TRACKER_BASE_URL` (internal Docker URL: `http://host.docker.internal:3007`)
- Browser-facing share URLs use `TOKEN_TRACKER_PUBLIC_URL` (e.g., `https://tracker.celox.io`)
- Customer `token_tracker_url` stores JSON: `[{"url":"...","label":"..."},...]` for multi-project support
- `TokenUsage.tsx` fetches from multiple URLs and merges data client-side

### Document Templates
- `routers/documents.py` generates legal document PDFs from templates with customer placeholder replacement
- Digital signature loaded from `/data/assets/signature-docs.png` (cropped) or fallback `SIGNATURE_PATH`
- ZIP download generates all 10 templates for one customer in a single archive (flat, no subfolders)
- Templates seeded via `POST /api/documents/templates/seed` (idempotent)

### PageSpeed Integration
- `routers/pagespeed.py` calls Google PageSpeed Insights API v5
- Results stored in `pagespeed_results` table with scores, PDF path, and customer link
- PDFs saved to `/data/pagespeed/` volume; list/delete/download via dedicated endpoints
- Customer detail page shows PageSpeed tab (when website set) with color-coded score table
- Optional `PAGESPEED_API_KEY` for higher quota (set in .env)

### Attachments / Documents
- `FileAttachments` component with drag & drop upload, description + notes (inline-editable)
- Upload: FormData with 20MB server-side limit. Filenames sanitized via `PurePosixPath(name).name`.
- PATCH endpoint: JSON body (`AttachmentUpdate` Pydantic model), NOT FormData.
- Orphan file cleanup: Upload writes file to disk first, then DB insert in try/except — file removed on DB failure.
- Files stored at `/data/attachments/` in Docker volume.

## Key Gotchas
- **Pydantic `date` field shadowing**: If a model has a field named `date`, import as `from datetime import date as DateType` to avoid `date | None` failing in subsequent classes in the same file.
- **Docker .env `$` escaping**: bcrypt hashes in `ADMIN_PASSWORD_HASH` must escape `$` as `$$`.
- **page_size limit**: Set to `le=1000` on all list endpoints (frontend requests 1000 for dropdowns).
- **PDF footer**: Use `@page @bottom-center` in CSS, NOT `position: fixed` (causes overlap with content).
- **Nginx timeout**: Set to 120s in `nginx/default.conf` for PageSpeed and other long-running API calls. Max body size 10M.
- **Nginx 502 after deploy**: Always restart nginx after rebuilding containers (new container IPs).
- **Signature in documents**: Image goes ABOVE the line (`border-top`), text BELOW. Signature HTML is a placeholder `{signature_html}` replaced during rendering.
- **Discount storage**: Stored as `discount_type` (percent/fixed), `discount_value`, `discount_reason` on Invoice model — NOT as negative positions. Guard: `discount_value is not None and discount_value != 0`.
- **Special terms**: Stored as JSON array string in `special_terms` field. Single string also supported (backward compatible).
- **Async httpx in refresh-drafts**: Uses `httpx.AsyncClient` (not sync `httpx.get`) to avoid blocking the event loop.
- **PDF generation in threads**: All `generate_*_pdf()` calls wrapped via `asyncio.to_thread()` since WeasyPrint is sync and would block the event loop for 2-5s per render.
- **CORS_ORIGINS env var required**: Empty value blocks all cross-origin requests. Set to `https://ops.celox.io` (or local dev origin) in `.env`.
- **JWT_SECRET startup validation**: Server refuses to start if `JWT_SECRET` is the default `"change-me-in-production"` or shorter than 32 chars. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Stats cache**: `/api/dashboard/stats` cached in-memory for 60s (`_stats_cache` in `routers/dashboard.py`). **AuditMiddleware** calls `invalidate_stats_cache()` after every successful mutating `/api/` request (2xx/3xx, excluding `/api/dashboard/*`) — so mark-paid/edit/delete reflects on the dashboard instantly, not after 60s. Overdue-Cron invalidates too when it flips statuses. Container restart also clears the cache (in-memory).
- **Customer relationships are `lazy="raise"`**: Don't access `customer.orders/contracts/invoices` without explicit `joinedload()` in the query — will throw at runtime.
- **Attachment MIME whitelist**: Only PDF, images, Office, ZIP accepted. Other types → 415. Whitelist in `routers/attachments.py`.
- **Login rate limit**: 5/min/IP via `slowapi`. Decorator on `auth.login`, exception handler in `main.py`.
- **2FA**: TOTP via `pyotp`. If `TOTP_SECRET` set, login requires 6-digit code in `scope` field of OAuth2 form. Frontend Login.tsx shows TOTP input on first 401 with detail "2FA-Code erforderlich". Default: empty (2FA off). To re-enable: scan QR from `/api/auth/2fa/setup`, save secret to `TOTP_SECRET` in `.env`, restart backend.
- **401 interceptor exception**: `api/client.ts` redirects to `/login` on 401 ONLY when the request is NOT to `/auth/login` AND the user is NOT already on `/login`. Otherwise the user gets bounced before seeing form errors (e.g. wrong password, 2FA required).
- **ServiceWorker is network-first**: `frontend/public/sw.js` always fetches from network, falls back to cache only offline. Cache name `celox-ops-v3` — bump to force purge. Avoids stale bundles after auto-deploy.
- **Public auth info endpoint**: `GET /api/auth/info` returns `{totp_enabled: bool}` without auth — frontend can pre-render the 2FA field if 2FA is active.
- **Audit log + cache invalidation**: Middleware in `app/middleware/audit.py` (1) logs all mutating requests to `audit_log` (best-effort — never blocks the response), (2) invalidates the dashboard stats cache after every successful mutating `/api/` request. Both run only for POST/PUT/PATCH/DELETE on `/api/*`, with `/api/auth/login` + `/api/health` skipped.
- **Auto-deploy**: VPS runs `scripts/auto-deploy.sh` every 5 minutes (cron). Polls `origin/main`, rebuilds only what changed. Repo at `/opt/celox-ops` was initialized with `git init && git remote add && git checkout -f main` (preserved `.env` via `/tmp/.env.backup`).
- **Backup**: `scripts/backup.sh` runs via cron at 03:00 daily. Outputs to `/var/backups/celox-ops/`. Optional rclone push to remote `celox-backup:`.
- **iCal feed**: `/api/ical?token=…` is PUBLIC (no JWT auth) — secured only by `ICAL_TOKEN` env var. Don't share the URL.
- **Smoke tests**: `backend/tests/test_smoke.py` — run inside container: `docker exec celox-ops-backend-1 python3 -m pytest test_smoke.py`. CI runs on every push.
- **Pre-commit vs CI scope**: `.pre-commit-config.yaml` runs `ruff --fix` only on **staged** files; GitHub Actions runs `ruff check backend/` over the **whole** backend tree. Always run `ruff check backend/` locally before pushing larger changes to catch pre-existing lint debt that the hook misses.
- **Axios FormData uploads**: The default `Content-Type: application/json` on the axios client (`api/client.ts`) prevents Axios from auto-detecting FormData and setting the multipart boundary. For file uploads, pass `headers: { 'Content-Type': undefined }` to override the default — otherwise backend gets 422.
- **Refresh-drafts position detection**: Auto-generated positions are marked with `"auto": true`. Legacy data detected via regex `\(\d{4}-\d{2}-\d{2} – \d{4}-\d{2}-\d{2}\)$`. Title-based matching was removed because renaming the invoice caused duplication.
- **Invoice detail display**: `positions[].gesamt` values from JSON may be strings — always wrap in `Number()` before arithmetic.
- **.env is NEVER committed**. All personal data (address, bank, tax, tokens) only in `.env` on the server.
- **.claude/ directory**: Added to `.gitignore` — contains local settings with server IPs, never commit.

## Database Tables (19)
customers, orders, contracts, invoices, leads, time_entries, expenses, activities, attachments, email_templates, document_templates, pagespeed_results, audit_log, rainmaker_leads, rainmaker_activities, rainmaker_settings, rainmaker_streak, rainmaker_templates, rainmaker_goal

Tables are auto-created on startup via `Base.metadata.create_all`. New columns on existing tables require manual `ALTER TABLE` on the running DB container. Backup auto-discovers all tables via `Base.registry.mappers`.
