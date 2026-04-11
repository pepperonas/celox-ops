# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

celox ops is a full-stack business management webapp for freelancers/IT consultants. German-language UI. Single-user JWT auth. Manages customers, orders, contracts, invoices (with PDF generation), leads, time tracking, expenses, and integrates with the Claude Token Tracker for AI usage transparency.

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

### Database
```bash
# Add column (no Alembic auto-migrate — tables created via Base.metadata.create_all on startup)
docker exec celox-ops-db-1 psql -U celoxops -d celoxops -c "ALTER TABLE tablename ADD COLUMN colname TYPE;"
```

### Deployment to VPS
```bash
tar czf /tmp/celox-ops.tar.gz --exclude='.git' --exclude='node_modules' --exclude='.DS_Store' --exclude='._*' --exclude='.env' .
scp /tmp/celox-ops.tar.gz root@YOUR_VPS:/tmp/
ssh root@YOUR_VPS 'cd /opt/celox-ops && tar xzf /tmp/celox-ops.tar.gz && rm /tmp/celox-ops.tar.gz && find . -name "._*" -delete && docker compose up -d --build'
```

## Architecture

### Backend (Python 3.12, FastAPI)
- **Entry point**: `backend/app/main.py` — FastAPI app with lifespan (creates tables + starts hourly cron)
- **Config**: `backend/app/config.py` — Pydantic Settings, all from `.env`
- **Database**: `backend/app/database.py` — async SQLAlchemy 2.0 with asyncpg, connection pooling
- **Auth**: `backend/app/auth.py` — JWT (python-jose), single-user, OAuth2PasswordBearer
- **Pattern**: Each module has model → schema → router. All routers registered in main.py after app creation (to avoid circular imports).
- **Models inherit from `Base`** defined in `models/customer.py`. New models MUST import Base from there.
- **All list endpoints return paginated**: `{items: [], total, page, page_size, pages}` — NOT plain arrays.
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
- **Theme**: GitHub-inspired dark theme. Colors defined as CSS variables in `index.css` AND as Tailwind custom colors in `tailwind.config.ts`. Key colors: `bg` (#0d1117), `surface` (#161b22), `accent` (#58a6ff).
- **Charts**: Chart.js + react-chartjs-2. Cast options as `any` to avoid TS issues with Chart.js types.
- **Tab persistence**: CustomerDetail uses URL hash (`#auftraege`, `#dokumente`, `#tokens`) for tab state.
- **Attachments**: `FileAttachments` component with drag & drop, description + notes (inline-editable). PATCH endpoint uses JSON body (not FormData). Upload uses FormData with 20MB server-side limit.

### Token Tracker Integration
- Backend proxies to Token Tracker via `TOKEN_TRACKER_BASE_URL` (internal Docker URL: `http://host.docker.internal:3007`)
- Browser-facing share URLs use `TOKEN_TRACKER_PUBLIC_URL` (e.g., `https://tracker.celox.io`)
- Customer `token_tracker_url` stores JSON: `[{"url":"...","label":"..."},...]` for multi-project support
- `TokenUsage.tsx` fetches from multiple URLs and merges data client-side

### Key Gotchas
- **Pydantic `date` field shadowing**: If a model has a field named `date`, import as `from datetime import date as DateType` to avoid `date | None` failing in subsequent classes in the same file.
- **Docker .env `$` escaping**: bcrypt hashes in `ADMIN_PASSWORD_HASH` must escape `$` as `$$`.
- **page_size limit**: Set to `le=1000` on all list endpoints (frontend requests 1000 for dropdowns).
- **PDF footer**: Use `@page @bottom-center` in CSS, NOT `position: fixed` (causes overlap with content).
- **.env is NEVER committed**. All personal data (address, bank, tax, tokens) only in `.env` on the server.

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
- Nginx proxy timeout must be ≥120s for slow API responses

### Key Gotchas (continued)
- **Nginx timeout**: Set to 120s in `nginx/default.conf` for PageSpeed and other long-running API calls
- **Signature in documents**: Image goes ABOVE the line (`border-top`), text BELOW. Signature HTML is a placeholder `{signature_html}` replaced during rendering.
- **Discount storage**: Stored as `discount_type` (percent/fixed), `discount_value`, `discount_reason` on Invoice model — NOT as negative positions. Guard in `invoice_service.py` uses `discount_value is not None and discount_value != 0`.
- **Special terms**: Stored as JSON array string in `special_terms` field. Single string also supported (backward compatible).
- **Attachment fields**: `description` (String 500) and `notes` (String 2000) on Attachment model. PATCH endpoint accepts JSON body (`AttachmentUpdate` Pydantic model), NOT FormData.
- **Path traversal prevention**: Attachment filenames sanitized via `PurePosixPath(name).name` before storage.
- **Orphan file cleanup**: Upload writes file first, then DB insert in try/except — file removed on DB failure.
- **Async httpx in refresh-drafts**: Uses `httpx.AsyncClient` (not sync `httpx.get`) to avoid blocking the event loop.
- **Invoice detail display**: `positions[].gesamt` values from JSON may be strings — always wrap in `Number()` before arithmetic.
- **.claude/ directory**: Added to `.gitignore` — contains local settings with server IPs, never commit.

## Database Tables (12)
customers, orders, contracts, invoices, leads, time_entries, expenses, activities, attachments, email_templates, document_templates, pagespeed_results

Tables are auto-created on startup via `Base.metadata.create_all`. New columns on existing tables require manual `ALTER TABLE` on the running DB container. Backup auto-discovers all tables via `Base.registry.mappers`.
