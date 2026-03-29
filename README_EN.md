<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/← Back-README-black?style=flat-square" alt="Back"></a>
  &nbsp;
  <a href="README_DE.md"><img src="https://img.shields.io/badge/%F0%9F%87%A9%F0%9F%87%AA-Deutsch-black?style=flat-square" alt="Deutsch"></a>
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="celox ops" width="1024">
</p>

# celox ops

Business-management web app for freelancers and IT consultants. Manages customers, orders, contracts, and invoices with professional PDF generation, AI usage tracking, and a German-language UI. Single-user application with JWT authentication.

---

## Features

### Customer Management
- Master data (name, company, email, phone, address, website)
- Overview of linked orders, contracts, and invoices per customer
- Full-text search across all fields
- Deletion protection when references exist

### Order Management
- Status workflow: **Angebot → Beauftragt → In Arbeit → Abgeschlossen** (or Storniert)
- Color-coded status badges
- Optional fields for amount, hourly rate, and time period
- **Quote PDF generation** for orders in status 'Angebot' with positions table and validity date
- Optional positions table with dynamic line items
- Download and email quote PDFs

### Contract Management
- Contract types: Hosting, Wartung (Maintenance), Support, Sonstige (Other)
- Auto-renewal with configurable notice period
- Configurable billing cycle (monthly, quarterly, semi-annual, annual)
- Monthly amount tracking

### Invoices
- **Auto-generated invoice numbers** in format `CO-YYYY-NNNN` (sequential per year)
- **Dynamic line items** — add/remove rows with live calculation
- Net/VAT/gross calculated automatically
- Status workflow: Entwurf → Gestellt → Bezahlt (or Überfällig/Storniert)
- Optional link to orders or contracts
- **Kleinunternehmerregelung** (small business tax exemption) — configurable, affects calculation and PDF text

### Quick Invoices
- One-click creation from customer detail page
- Single line item with description and amount
- Auto invoice number, 14-day payment term

### Recurring Invoices
- Auto-generate draft invoices from active contracts based on billing cycle
- Calculates due dates from billing_cycle + last_invoiced_date
- German period labels (März 2026, Q1 2026, 1. Halbjahr 2026)
- One-click generation from Tasks page
- Amounts calculated from monthly_amount × cycle multiplier

### AI Time Import
- Import active AI working time and API costs directly into invoice line items
- Configurable hourly rate (default 95 €/h)
- Selectable date range for the import period
- Auto-creates two positions: work hours × rate + API costs as flat fee
- Only visible when customer has Token Tracker linked
- Automatically sets the AI usage report attachment period

### Dunning System (Mahnwesen)
- Three-level reminder workflow: Zahlungserinnerung → 1. Mahnung → Letzte Mahnung
- Professional PDF templates with level-dependent text
- Reminder level tracking on each invoice
- Generate and download reminder PDFs
- Send reminders via email directly from the app

### Time Tracking (Zeiterfassung)
- Start/stop timer with customer assignment (persisted in localStorage)
- Manual time entries with date, hours, hourly rate, description
- Per-customer summary: open hours, total amount, uninvoiced entries
- Filter by customer and date range
- Track billable hours for non-AI work (meetings, calls, configuration)

### PDF Generation
- Professional A4 invoice PDFs with customizable branding
- Generated via **WeasyPrint** with Jinja2 templates
- Includes: sender, recipient, line items, totals, bank details, tax info
- **Signature image** embedded (base64, configurable path)
- **Payment options**: bank transfer (IBAN/BIC) and PayPal (configurable)
- **Tax number** in footer (Steuernummer, as required by German tax law)
- Optional **AI usage report** attachment with selectable date range
- **In-browser PDF viewer** — view invoices, quotes, and reminders directly in a new tab
- Default period for AI usage report: 1st of current month to today

### Email Sending
- Send invoices, quotes, and reminders directly via SMTP
- Configurable SMTP settings (host, port, TLS, credentials)
- Pre-filled recipient, subject, and message templates
- Reusable email dialog with editable fields
- PDF automatically attached

### Activity Log (Kontakthistorie)
- Per-customer timeline of all interactions
- Automatic logging: invoice created, reminder sent, email sent, order/contract created
- Manual entries: notes, calls, emails, meetings
- Color-coded by type with relative timestamps
- New tab on customer detail page

### AI Usage Tracking (Token Tracker Integration)
- Integration with [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) via secure Share API
- **Multi-project linking** — multiple Token Tracker projects per customer, data automatically merged across projects
- **Labels stored at link time** — project labels captured when linked, no extra API calls needed
- **Period filter** — 7/30/90 days, all time, or custom date range
- **KPI cards**: cost, active work time, code lines written, AI requests
- **Charts** (Chart.js): daily work intensity, cumulative cost trend, code development
- **Sessions table**: date, active duration, AI model, requests, code lines, cost
- **Active time tracking** — measures real working time (not session duration) based on message intervals with 5-min gap threshold; intervals between consecutive AI interactions are summed, gaps > 5 minutes counted as inactive
- **CSV export** and **HTML report** generation for sending to clients
- Customer-friendly labels — "Arbeitssitzungen" instead of "Sessions", "Codezeilen" instead of "Tokens"
- AI usage report can be **attached to invoice PDFs** as a second page

### Leads (Vorgemerkt)
- Track potential clients and websites for outreach
- Simple list with URL (required), name, company, email, phone, notes, and status workflow (Neu → Kontaktiert → Interessiert → Abgelehnt)
- Full-text search across all fields
- Built-in website quality analyzer (SSL, load time, mobile, SEO, accessibility, security headers)
- Score 0-100% with color-coded progress bar
- Findings grouped by category with severity levels
- Quick arguments panel for sales calls

### Expenses
- 10 categories (Hosting, Domain, Software, License, Hardware, AI/API, Advertising, Office, Travel, Other)
- Recurring expense flag
- Summary KPIs (yearly/monthly total, top category)

### Income Statement (EÜR)
- Automatic calculation from paid invoices (revenue) minus expenses
- Year selector with monthly and quarterly breakdown
- Chart.js bar chart: revenue vs expenses per month
- Quarterly cards with revenue/expenses/profit
- Monthly detail table with color-coded profit
- Expense breakdown by category with progress bars
- CSV export for tax advisor

### Dashboard
- Revenue current month and year
- Open invoices (count + total)
- Overdue invoices (highlighted)
- Active contracts (count + monthly sum)

### Tasks (Aufgaben)
- Aggregated todo list of upcoming actions
- Overdue invoices (critical priority)
- Invoices due within 30 days
- Draft invoices not yet sent
- Contracts expiring within 60 days
- Active orders in progress
- Color-coded by priority (critical/warning/info)
- Click-through to relevant detail pages

### Settings
- Token Tracker connection status
- Configuration guide for Token Tracker integration
- **Database backup** — one-click export of all data (customers, orders, contracts, invoices, leads, time entries, expenses, activities) as JSON file
- PDFs included as Base64 in the backup — everything in a single file

### Smart Autocomplete
- Title fields in invoices and orders suggest ~80 IT consulting services while typing
- Position descriptions suggest ~80 detailed task descriptions (development, SEO, hosting, security, etc.)
- Keyboard navigation (arrow keys + Enter), filtered as you type
- Categories: Website, SEO, Hosting, Development, Consulting, Maintenance, Security, AI

### Design
- **GitHub-inspired dark theme**
- Color palette: `#0d1117` (background), `#161b22` (surfaces), `#58a6ff` (accent)
- Responsive layout with collapsible sidebar
- Sidebar navigation: Dashboard, Aufgaben, Zeiterfassung, Kunden, Aufträge, Verträge, Rechnungen, Vorgemerkt, Ausgaben, EÜR, Einstellungen
- Consistent status badges, tables, and form components
- Tab state persisted in URL hash across page refreshes

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18, TypeScript, TailwindCSS | SPA with typed components |
| **Bundler** | Vite 6 | Fast build + HMR |
| **State** | Zustand | Lightweight auth state |
| **HTTP** | Axios | API client with JWT interceptor |
| **Charts** | Chart.js + react-chartjs-2 | Interactive AI usage charts |
| **Backend** | Python 3.12, FastAPI | Async REST API with OpenAPI docs |
| **Validation** | Pydantic v2 | Request/response schemas |
| **ORM** | SQLAlchemy 2.0 (async) | Async database access |
| **Database** | PostgreSQL 16 | Relational storage via asyncpg |
| **Migrations** | Alembic | Schema versioning |
| **PDF** | WeasyPrint + Jinja2 | HTML-to-PDF invoice generation |
| **Auth** | JWT (python-jose + passlib) | Token-based auth with bcrypt |
| **Infra** | Docker Compose | Multi-container orchestration |
| **Proxy** | Nginx | Reverse proxy + static files |

---

## Data Model

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   customers  │     │    orders    │     │  contracts   │
│──────────────│     │──────────────│     │──────────────│
│ id (UUID)    │◄────│ customer_id  │     │ customer_id  │────►│
│ name         │     │ title        │     │ title        │
│ email        │     │ status       │     │ type         │
│ phone        │     │ amount       │     │ monthly_amt  │
│ company      │     │ hourly_rate  │     │ auto_renew   │
│ address      │     │ start_date   │     │ notice_days  │
│ website      │     │ end_date     │     │ status       │
│ token_tracker│     └──────┬───────┘     └──────┬───────┘
│  _url        │            │                     │
│ notes        │            ▼                     ▼
└──────────────┘     ┌──────────────┐
                     │   invoices   │
                     │──────────────│
                     │ customer_id  │
                     │ order_id?    │
                     │ contract_id? │
                     │ invoice_nr   │  ← CO-YYYY-NNNN
                     │ positions[]  │  ← JSONB
                     │ subtotal     │
                     │ tax_rate     │
                     │ tax_amount   │
                     │ total        │
                     │ status       │
                     │ pdf_path     │
                     │ token_usage_ │
                     │  from / to   │
                     └──────────────┘
```

---

## API Overview

All endpoints under `/api/`, protected via JWT Bearer Token.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login (OAuth2 form → JWT) |
| `GET` | `/api/auth/me` | Current user |
| `GET` | `/api/customers` | Customer list (search, pagination, sorting) |
| `GET` | `/api/customers/{id}` | Customer detail with reference counts |
| `POST` | `/api/customers` | Create customer |
| `PUT` | `/api/customers/{id}` | Update customer |
| `DELETE` | `/api/customers/{id}` | Delete customer (with reference check) |
| `GET` | `/api/orders` | Order list (filter: status, customer) |
| `POST/PUT/DELETE` | `/api/orders/{id}` | CRUD for orders |
| `GET` | `/api/contracts` | Contract list (filter: status, type) |
| `POST/PUT/DELETE` | `/api/contracts/{id}` | CRUD for contracts |
| `GET` | `/api/invoices` | Invoice list (filter: status, customer) |
| `POST` | `/api/invoices` | Create invoice (auto number) |
| `POST` | `/api/invoices/quick` | Quick invoice (single position) |
| `PUT` | `/api/invoices/{id}` | Update invoice |
| `PUT` | `/api/invoices/{id}/status` | Change status |
| `POST` | `/api/invoices/{id}/generate-pdf` | Generate PDF |
| `GET` | `/api/invoices/{id}/pdf` | Download PDF |
| `DELETE` | `/api/invoices/{id}` | Delete (drafts only) |
| `GET` | `/api/dashboard/stats` | Dashboard KPIs |
| `GET` | `/api/tasks` | Aggregated task list |
| `GET` | `/api/token-tracker/projects` | Projects from Token Tracker |
| `GET/POST` | `/api/token-tracker/shares` | Manage share tokens |
| `DELETE` | `/api/token-tracker/shares/{id}` | Revoke share |
| `GET` | `/api/leads` | Lead list (search, status filter, pagination) |
| `POST` | `/api/leads` | Create lead |
| `PUT` | `/api/leads/{id}` | Update lead |
| `DELETE` | `/api/leads/{id}` | Delete lead |
| `POST` | `/api/invoices/generate-recurring` | Generate recurring invoices |
| `POST` | `/api/invoices/{id}/remind` | Send payment reminder |
| `POST` | `/api/invoices/{id}/send-email` | Send invoice via email |
| `POST` | `/api/invoices/{id}/send-reminder-email` | Send reminder via email |
| `POST` | `/api/invoices/{id}/generate-reminder-pdf` | Generate reminder PDF |
| `GET` | `/api/invoices/{id}/reminder-pdf` | Download reminder PDF |
| `GET/POST/PUT/DELETE` | `/api/time-entries` | Time entry CRUD |
| `GET` | `/api/time-entries/summary` | Time entry summary |
| `POST` | `/api/orders/{id}/generate-quote-pdf` | Generate quote PDF |
| `GET` | `/api/orders/{id}/quote-pdf` | Download quote PDF |
| `POST` | `/api/orders/{id}/send-quote-email` | Send quote via email |
| `GET` | `/api/activities?customer_id=` | Activity log |
| `POST` | `/api/activities` | Create activity |
| `GET/POST/PUT/DELETE` | `/api/expenses` | Expense CRUD |
| `GET` | `/api/expenses/summary` | Expense summary |
| `GET` | `/api/euer/overview` | EÜR overview |
| `GET` | `/api/euer/export` | EÜR CSV export |
| `GET` | `/api/backup/export` | Full database export (JSON + PDFs) |
| `GET` | `/api/health` | Health check |

Interactive API docs at `/docs` (Swagger UI).

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

```bash
git clone https://github.com/pepperonas/celox-ops.git
cd OPS

# Configure environment
cp .env.example .env
# Edit .env: set passwords, JWT_SECRET, business details
# Generate password hash:
#   python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"
# Escape $ as $$ in .env for Docker Compose

# Start
docker compose up -d --build

# App available at http://localhost:8090
```

### Development

```bash
docker compose -f docker-compose.dev.yml up -d --build

# Backend:  http://localhost:8000 (auto-reload)
# Frontend: http://localhost:5173 (Vite HMR)
# API Docs: http://localhost:8000/docs
# DB:       localhost:5433 (PostgreSQL)
```

---

## Deployment

Designed for deployment behind a reverse proxy with SSL termination (e.g., Nginx + Let's Encrypt).

- **Port**: 8090 (Docker) — proxy to your domain
- **Data persistence**: Docker volumes for PostgreSQL and PDF storage
- **SSL**: Configure on your host reverse proxy

```bash
docker compose up -d --build
```

---

## Better Together: Token Tracker Integration

celox ops and the [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) form a complete consulting toolkit. OPS handles the business side (customers, invoices, contracts), while Token Tracker captures the AI development metrics (sessions, tokens, cost, code output).

### Data Flow

```
Claude Code → Token Tracker → Share API → celox ops → Customer Dashboard + Invoice PDF
```

1. **Claude Code** generates usage data during AI-assisted development
2. **Token Tracker** collects and stores per-project metrics (tokens, cost, code lines, active time)
3. **Share API** provides secure, token-based access to project metrics
4. **celox ops** pulls metrics into the customer detail page and renders interactive dashboards
5. **Invoice PDFs** can include an AI usage report as an attachment page

### Benefits for the Consultant
- **Transparent billing** — every hour of AI-assisted work is documented with verifiable metrics
- **Automated reporting** — no manual time tracking or report writing needed
- **Client trust** — customers can see exactly what was done, how long it took, and what it cost
- **One-click invoicing** — generate a professional PDF with AI report attached in seconds

### Benefits for the Customer
- **Verifiable work documentation** — session-level detail of all AI-assisted development
- **Active time tracking** — real working time based on interaction patterns, not inflated session durations
- **Cost transparency** — see AI costs per session, per day, and cumulative trends
- **Exportable reports** — CSV and HTML exports for their own records

### Setup

1. **Token Tracker**: Go to Settings → Share API → copy the Admin Key
2. **celox ops `.env`**: Set `TOKEN_TRACKER_BASE_URL` and `TOKEN_TRACKER_ADMIN_KEY`
3. **Link project**: Customer → Edit → "Projekt verknüpfen" → select project

### Security

- Share tokens: 192-bit cryptographically random (48-char hex)
- Admin key: 256-bit, required for share management
- Public endpoint rate-limited (30 req/min per IP)
- CORS restricted to configured origins
- No project enumeration possible
- Optional expiry on share tokens
- No internal paths or identifiers exposed

### Active Time Tracking

Active working time is calculated from message timestamps: intervals between consecutive AI interactions are summed, with gaps > 5 minutes counted as inactive. This gives realistic work time (e.g., "5h 15min" instead of "194h session duration").

---

## Configuration (.env)

| Variable | Description | Example |
|----------|------------|---------|
| `POSTGRES_USER` | Database user | `celoxops` |
| `POSTGRES_PASSWORD` | Database password | `secure-password` |
| `DATABASE_URL` | Async connection string | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Token signing key | (random, 48+ chars) |
| `ADMIN_USERNAME` | Login username | `admin` |
| `ADMIN_PASSWORD_HASH` | bcrypt hash of password | `$$2b$$12$$...` |
| `BUSINESS_NAME` | Company name (PDFs) | `Your Company` |
| `BUSINESS_OWNER` | Owner name (PDFs) | `Your Name` |
| `BUSINESS_ADDRESS` | Address (PDFs) | `Street, ZIP City` |
| `BUSINESS_EMAIL` | Email (PDFs) | `info@example.com` |
| `BUSINESS_TAX_ID` | VAT ID | `DE...` |
| `BUSINESS_BANK_*` | Bank details (IBAN, BIC, name) | for invoice PDF |
| `BUSINESS_PAYPAL` | PayPal address (optional) | `you@example.com` |
| `KLEINUNTERNEHMER` | Small business exemption | `true` / `false` |
| `PDF_STORAGE_PATH` | PDF storage path | `/data/invoices` |
| `SIGNATURE_PATH` | Signature image path (optional) | `/data/assets/signature.png` |
| `TOKEN_TRACKER_BASE_URL` | Token Tracker URL (optional) | `http://host:port` |
| `TOKEN_TRACKER_PUBLIC_URL` | Public Token Tracker URL (for browser) | `https://tracker.example.com` |
| `TOKEN_TRACKER_ADMIN_KEY` | Share Admin Key (optional) | (64-char hex) |
| `SMTP_HOST` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | `user@example.com` |
| `SMTP_PASSWORD` | SMTP password | (app password) |
| `SMTP_FROM_EMAIL` | Sender email | `info@example.com` |
| `SMTP_FROM_NAME` | Sender name | `Your Company` |

**Security notes:**
- Never commit `.env` — it is in `.gitignore`
- Generate strong values for `JWT_SECRET` and `POSTGRES_PASSWORD`
- The `ADMIN_PASSWORD_HASH` must be a bcrypt hash (escape `$` as `$$`)
- `TOKEN_TRACKER_ADMIN_KEY` is only needed if using the Token Tracker integration
- `SIGNATURE_PATH` must point to a PNG inside the Docker volume (`/data/assets/`)
- All personal data (address, tax number, bank details, PayPal) is stored exclusively in `.env` — never in code or templates
- Database backups contain all business data — store securely and do not share

---

## Project Structure

```
OPS/
├── docker-compose.yml          # Production: db, backend, frontend, nginx
├── docker-compose.dev.yml      # Development with hot-reload
├── .env.example                # Environment variable template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # Database migrations
│   └── app/
│       ├── main.py             # FastAPI app, CORS, lifespan
│       ├── config.py           # Pydantic Settings (env-based)
│       ├── database.py         # SQLAlchemy engine + async session
│       ├── auth.py             # JWT login, token validation
│       ├── models/             # SQLAlchemy 2.0 Mapped models
│       │   ├── ...
│       │   ├── lead.py         # Lead model
│       │   ├── time_entry.py   # Time entry model
│       │   ├── activity.py     # Activity log model
│       │   └── expense.py      # Expense model
│       ├── schemas/            # Pydantic v2 request/response schemas
│       │   ├── time_entry.py   # Time entry schemas
│       │   ├── activity.py     # Activity log schemas
│       │   ├── expense.py      # Expense schemas
│       │   └── ...
│       ├── routers/            # API endpoints (all paginated)
│       │   ├── customers.py    # CRUD + search + reference check
│       │   ├── orders.py       # CRUD + status/customer filter
│       │   ├── contracts.py    # CRUD + status/type filter
│       │   ├── invoices.py     # CRUD + PDF + status + quick invoice
│       │   ├── dashboard.py    # Aggregated KPIs
│       │   ├── leads.py         # Lead CRUD + search + status filter
│       │   ├── tasks.py         # Aggregated task list
│       │   ├── time_entries.py  # Time entry CRUD + summary
│       │   ├── activities.py   # Activity log endpoints
│       │   ├── expenses.py     # Expense CRUD + summary
│       │   ├── euer.py         # EÜR overview + CSV export
│       │   ├── backup.py       # Full database export (JSON + PDFs)
│       │   └── token_tracker.py # Token Tracker share API proxy
│       ├── services/
│       │   ├── invoice_service.py  # Invoice number + calculation
│       │   ├── pdf_service.py      # WeasyPrint + Jinja2 + AI report
│       │   └── email_service.py    # SMTP email sending
│       └── templates/
│           ├── invoice.html    # A4 invoice PDF template
│           ├── reminder.html   # Reminder/dunning PDF template
│           └── quote.html      # Quote PDF template
│
├── frontend/
│   ├── Dockerfile              # Multi-stage: build → Nginx
│   ├── package.json
│   ├── tailwind.config.ts      # Custom dark theme
│   └── src/
│       ├── App.tsx             # Routing
│       ├── api/                # Axios API client + CRUD functions
│       │   ├── timeEntries.ts  # Time entry API
│       │   ├── activities.ts   # Activity log API
│       │   ├── expenses.ts     # Expense API
│       │   ├── euer.ts         # EÜR API
│       │   └── ...
│       ├── components/
│       │   ├── Layout.tsx      # Sidebar + header
│       │   ├── DataTable.tsx   # Sortable, paginated
│       │   ├── TokenUsage.tsx  # AI usage dashboard (charts, KPIs, export)
│       │   ├── EmailDialog.tsx # Reusable email sending dialog
│       │   ├── AutocompleteInput.tsx # Smart autocomplete for titles/descriptions
│       │   └── ...             # StatusBadge, FormField, DeleteDialog, Toast
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── Tasks.tsx       # Aggregated task view
│       │   ├── TimeTracking.tsx # Time tracking page
│       │   ├── Euer.tsx        # EÜR overview page
│       │   ├── customers/      # List, form, detail
│       │   ├── orders/         # List, form, detail
│       │   ├── contracts/      # List, form, detail
│       │   ├── invoices/       # List, form, detail
│       │   ├── leads/          # List, form
│       │   └── expenses/       # List, form
│       └── utils/
│           ├── formatters.ts   # Date (DD.MM.YYYY), currency (1.234,56 EUR)
│           └── validators.ts
│
└── nginx/
    └── default.conf            # /api → backend, / → frontend
```

---

## Invoice Number Format

```
CO-2026-0001
│  │     │
│  │     └── Sequential number (zero-padded, per year)
│  └──────── Calendar year
└─────────── Configurable prefix
```

---

## Database Optimization

- PostgreSQL indexes on all foreign keys (customer_id on orders/contracts/invoices)
- Status indexes for filtered queries
- Partial index for open invoices (dashboard performance)
- Composite index on customer name+company for search
- Connection pooling: pool_size=5, max_overflow=10, pre_ping enabled, 5-min recycle
- Token Tracker aggregator cached with 5-min TTL (eliminates repeated full-table scans)

---

## License

MIT

---

*Built by [Martin Pfeffer](https://celox.io)*
