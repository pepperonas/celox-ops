<p align="center">
  <img src="docs/screenshot.png" alt="celox ops" width="1024">
</p>

# celox ops

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![WeasyPrint](https://img.shields.io/badge/WeasyPrint-PDF-E44D26)](https://weasyprint.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4-FF6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)](https://alembic.sqlalchemy.org/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![Zustand](https://img.shields.io/badge/Zustand-State-443E38)](https://zustand-demo.pmnd.rs/)
[![Axios](https://img.shields.io/badge/Axios-HTTP-5A29E4?logo=axios&logoColor=white)](https://axios-http.com/)

---

Business-Management-Webapp for freelancers and IT consultants. Manages customers, orders, contracts, and invoices with professional PDF generation, AI usage tracking, and a German-language UI. Single-user application with JWT authentication.

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

### Contract Management
- Contract types: Hosting, Wartung (Maintenance), Support, Sonstige (Other)
- Auto-renewal with configurable notice period
- Monthly amount tracking

### Invoices
- **Auto-generated invoice numbers** in format `CO-YYYY-NNNN` (sequential per year)
- **Dynamic line items** — add/remove rows with live calculation
- Net/VAT/gross calculated automatically
- Status workflow: Entwurf → Gestellt → Bezahlt (or Ueberfaellig/Storniert)
- Optional link to orders or contracts
- **Kleinunternehmerregelung** (small business tax exemption) — configurable, affects calculation and PDF text

### Quick Invoices
- One-click creation from customer detail page
- Single line item with description and amount
- Auto invoice number, 14-day payment term

### PDF Generation
- Professional A4 invoice PDFs with customizable branding
- Generated via **WeasyPrint** with Jinja2 templates
- Includes: sender, recipient, line items, totals, bank details, tax info
- Optional **AI usage report** attachment with selectable date range

### AI Usage Tracking (Token Tracker Integration)
- Integration with [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) via secure Share API
- **Period filter** — 7/30/90 days, all time, or custom date range
- **KPI cards**: cost, active work time, code lines written, AI requests
- **Charts** (Chart.js): daily work intensity, cumulative cost trend, code development
- **Sessions table**: date, active duration, AI model, requests, code lines, cost
- **Active time tracking** — measures real working time (not session duration) based on message intervals with 5-min gap threshold
- **CSV export** and **HTML report** generation for sending to clients
- Customer-friendly labels — "Arbeitssitzungen" instead of "Sessions", "Codezeilen" instead of "Tokens"
- AI usage report can be **attached to invoice PDFs** as a second page

### Dashboard
- Revenue current month and year
- Open invoices (count + total)
- Overdue invoices (highlighted)
- Active contracts (count + monthly sum)

### Settings
- Token Tracker connection status
- Configuration guide for Token Tracker integration

### Design
- **GitHub-inspired dark theme**
- Color palette: `#0d1117` (background), `#161b22` (surfaces), `#58a6ff` (accent)
- Responsive layout with collapsible sidebar
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
| `GET` | `/api/token-tracker/projects` | Projects from Token Tracker |
| `GET/POST` | `/api/token-tracker/shares` | Manage share tokens |
| `DELETE` | `/api/token-tracker/shares/{id}` | Revoke share |
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
cd celox-ops

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

## Token Tracker Integration

celox ops integrates with the [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) to provide customers with transparent insights into AI-assisted development work.

### How It Works

1. The Token Tracker monitors Claude Code usage and stores per-project metrics (tokens, cost, code lines, sessions)
2. celox ops connects via a secure Share Admin Key
3. Per customer, a share token is generated for their specific project
4. The customer detail page shows an interactive AI usage dashboard
5. Reports can be exported as CSV/HTML or attached to invoice PDFs

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
| `BUSINESS_BANK_*` | Bank details (IBAN, BIC) | for invoice PDF |
| `KLEINUNTERNEHMER` | Small business exemption | `true` / `false` |
| `PDF_STORAGE_PATH` | PDF storage path | `/data/invoices` |
| `TOKEN_TRACKER_BASE_URL` | Token Tracker URL (optional) | `http://host:port` |
| `TOKEN_TRACKER_ADMIN_KEY` | Share Admin Key (optional) | (64-char hex) |

**Security notes:**
- Never commit `.env` — it is in `.gitignore`
- Generate strong values for `JWT_SECRET` and `POSTGRES_PASSWORD`
- The `ADMIN_PASSWORD_HASH` must be a bcrypt hash (escape `$` as `$$`)
- `TOKEN_TRACKER_ADMIN_KEY` is only needed if using the Token Tracker integration

---

## Project Structure

```
celox-ops/
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
│       ├── schemas/            # Pydantic v2 request/response schemas
│       ├── routers/            # API endpoints (all paginated)
│       │   ├── customers.py    # CRUD + search + reference check
│       │   ├── orders.py       # CRUD + status/customer filter
│       │   ├── contracts.py    # CRUD + status/type filter
│       │   ├── invoices.py     # CRUD + PDF + status + quick invoice
│       │   ├── dashboard.py    # Aggregated KPIs
│       │   └── token_tracker.py # Token Tracker share API proxy
│       ├── services/
│       │   ├── invoice_service.py  # Invoice number + calculation
│       │   └── pdf_service.py      # WeasyPrint + Jinja2 + AI report
│       └── templates/
│           └── invoice.html    # A4 invoice PDF template
│
├── frontend/
│   ├── Dockerfile              # Multi-stage: build → Nginx
│   ├── package.json
│   ├── tailwind.config.ts      # Custom dark theme
│   └── src/
│       ├── App.tsx             # Routing
│       ├── api/                # Axios API client + CRUD functions
│       ├── components/
│       │   ├── Layout.tsx      # Sidebar + header
│       │   ├── DataTable.tsx   # Sortable, paginated
│       │   ├── TokenUsage.tsx  # AI usage dashboard (charts, KPIs, export)
│       │   └── ...             # StatusBadge, FormField, DeleteDialog, Toast
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── customers/      # List, form, detail
│       │   ├── orders/         # List, form, detail
│       │   ├── contracts/      # List, form, detail
│       │   └── invoices/       # List, form, detail
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

## License

MIT

---

*Built by [Martin Pfeffer](https://celox.io)*
