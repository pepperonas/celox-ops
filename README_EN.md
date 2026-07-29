<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/← Back-README-black?style=flat-square" alt="Back"></a>
  &nbsp;
  <a href="README_DE.md"><img src="https://img.shields.io/badge/%F0%9F%87%A9%F0%9F%87%AA-Deutsch-black?style=flat-square" alt="Deutsch"></a>
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="celox ops" width="1024">
</p>

# celox ops

Business-management web app for freelancers and IT consultants. Manages customers, orders, contracts, and invoices with professional PDF generation, AI usage tracking, and a German-language UI. **Multi-user with isolated workspaces** (per-user data isolation; admin-managed accounts) and JWT authentication.

---

## Features

### Customer Management
- Master data (name, company, email, phone, address, website)
- Overview of linked orders, contracts, and invoices per customer
- Full-text search across all fields
- Deletion protection when references exist
- **Document management** — dedicated tab per customer for file uploads (drag & drop, max 20 MB), with description and notes, editable after upload
- **DSGVO data export** — one-click export of all customer data (Art. 15 DSGVO)
- **Google PageSpeed Insights** — one-click PDF report with performance, accessibility, SEO scores

### Order Management
- Status workflow: **Angebot → Beauftragt → In Arbeit → Abgeschlossen** (or Storniert)
- Color-coded status badges
- Optional fields for amount, hourly rate, and time period
- **Quote PDF generation** for orders in status 'Angebot' with positions table and validity date
- Optional positions table with dynamic line items
- Download and email quote PDFs

### Kanban Board
- Visual order management with 4 columns: Angebot → Beauftragt → In Arbeit → Abgeschlossen
- Drag & drop cards between columns to change status
- Cards show title, customer, amount, date
- Color-coded column headers

### Contract Management
- Contract types: Hosting, Wartung (Maintenance), Support, Sonstige (Other)
- Auto-renewal with configurable notice period
- Configurable billing cycle (monthly, quarterly, semi-annual, annual)
- Monthly amount tracking

### Invoices
- **Auto-generated invoice numbers** in format `CO-YYYY-NNNN` (sequential per year)
- **Dynamic line items** — add/remove any row (including the last one) with live calculation
- Net/VAT/gross calculated automatically
- Status workflow: Entwurf → Gestellt → Bezahlt (or Überfällig/Storniert)
- Optional link to orders or contracts
- **Kleinunternehmerregelung** (small business tax exemption) — configurable, affects calculation and PDF text
- **Partial payments** — record payments, auto-complete when fully paid
- **Credit notes** (Gutschriften) — separate number series GS-YYYY-NNNN, linked to original invoice
- **Discount function** — percentage or fixed amount with autocomplete for reasons (275 suggestions: friends-and-family, early-payment discount, functional discount, SLA credit, price match, non-profit, and more)
- Discount shown as negative position on invoice PDF
- **Special terms** — unlimited per invoice with autocomplete (hosting, support, SSL, migrations, payment plans, etc.)
- **Multi-project billing** — select specific Token Tracker projects and GitHub repos per invoice via checkboxes
- **Activity chart attachment** — optional CSS bar chart showing daily work intensity in the PDF
- **Invoice number offset** — configurable for externally issued invoices (INVOICE_NUMBER_OFFSET in .env)
- **Gap-filling numbering** — deleted drafts free up their number for reuse (maintains sequential order)
- **Value-oriented positions** — AI import uses invoice title as position description, not generic "KI-gestützte Entwicklung"
- **Service description** — optional field shown prominently in PDF before line items (describe outcomes, not tools)
- **Full state persistence** — all toggles, date ranges, project selections, and discounts restored when editing
- **Unified date range** — GitHub commits and activity chart inherit the period from the AI usage report
- **One-click draft refresh** — update all drafts to today: set invoice date + payment term, re-import AI time (old auto-positions replaced, manual ones preserved), recalculate totals, regenerate PDFs
- **Per-invoice tax control** — checkbox to include/exclude VAT (Kleinunternehmerregelung per invoice, not just globally)
- **Complete detail view** — invoice detail page shows discount (subtotal, deduction, reason), special terms, service description, and tax exemption notice
- **Issued invoices are immutable in content (GoBD)** — from status "issued" onwards any change to line items, discount, VAT, date, customer or note is refused with a reason; **values are compared, not presence**, so a form submitted unchanged passes through. Status changes, payments and dunning levels stay possible — those are separate operations documenting the *process*, not the *content*. The correction path is **cancel (credit note) + duplicate**
- **Automatic PDF regeneration** — editing a draft automatically rebuilds an existing PDF so changes are immediately visible (in the background, keeping saves fast)
- **Free status correction** — a "Status ändern" dropdown with all 5 statuses (draft/issued/paid/overdue/cancelled) on the detail page, for misclicks
- **Undo** — every status change (detail page, quick buttons and bulk "mark paid" in the list) shows a toast with an undo button; bulk undo also reverts the recorded payments

### Quick Invoices
- One-click creation from customer detail page
- Single line item with description and amount
- Auto invoice number, 14-day payment term
- Autocomplete for description (nearly 500 title suggestions)
- Comma input for quantity and unit price (mobile shows decimal keyboard)

### Keyboard Shortcuts
- **Ctrl+S / ⌘S** — save form (in all 6 forms: invoice, customer, order, contract, expense, lead)
- **Esc** — leave form / close dialog
- **Enter** in delete dialog — confirm

### Undo & Error Tolerance
- **Global undo pattern** — reversible actions show a success toast with an undo button (8-second window)
- Covered: invoice status changes (incl. "mark paid" everywhere), order kanban drags, Rainmaker pipeline drags, bulk "mark paid" (incl. reverting recorded payments)
- **Restorable deletions** — expenses, time entries, customer activities and planned Rainmaker actions are re-created on undo
- Deliberately without undo: invoice/customer deletions (number sequence, PDFs, references — the confirmation dialog guards those) and completed Rainmaker actions (they carry points/streak)

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
- Auto-creates two positions: work hours × rate + API costs as flat fee (position "Technische Infrastruktur & externe Systemkosten (KI)")
- **Live USD→EUR** — conversion uses the daily ECB reference rate (Frankfurter API, 12 h cache, safe fallback) instead of a hardcoded factor
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
- **Optional logo** in header (`LOGO_PATH` env var)
- **Payment options**: bank transfer (IBAN/BIC) and PayPal (configurable)
- **Online payment link + QR code** in PDF (`PAYMENT_LINK_TEMPLATE` with `{amount}` + `{invoice_number}` placeholders, e.g. PayPal.me or Stripe link)
- **Tax number** in footer (Steuernummer, as required by German tax law)
- Up to 3 optional PDF attachments: AI usage report, GitHub commit history, or both — each with independent date range
- **In-browser PDF viewer** — view invoices, quotes, and reminders directly in a new tab
- Default period for AI usage report: 1st of current month to today

### Email Sending
- Send invoices, quotes, and reminders directly via SMTP
- Configurable SMTP settings (host, port, TLS, credentials)
- **Automatic SSL/TLS detection** — port 465 (SMTPS, implicit SSL) and port 587 (STARTTLS) handled automatically
- **CC + BCC recipients** in email dialog (multiple addresses via comma/semicolon, toggle "+ CC / BCC")
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

### GitHub Integration
- **Repository linking** — connect GitHub repos to customers via searchable picker (loads all repos from GitHub API)
- **Commit history in invoice PDFs** — separate toggle with independent date range
- Commits listed as 'Entwicklungsprotokoll' attachment: date, repo, commit message, author
- Can be combined with or used independently from AI usage report
- Private repos supported (requires GitHub token)

### Website analysis (pipeline leads)
> The former "Vorgemerkt" watchlist has been **removed**. Leads live in the
> **pipeline** (Rainmaker data model); old `/vorgemerkt` URLs redirect there permanently.

- **Stored and versioned** — every run is its own record on the lead (overall score, traffic light, per-category subscores, individual findings, detected technologies, recommendations); the lead itself carries score/rating/date so the list needs no join
- **Analysis → scoring → presentation kept separate** — checks cover privacy (imprint, GDPR link, cookie banner, 20 tracking services with risk rating, Google Fonts local vs. external), performance, SEO (title/description lengths, H1–H6 structure, ALT ratio, JSON-LD, robots.txt/sitemap, broken links), tech (HTTPS, security headers, CMS/framework/CDN detection) and UX; weighted into one score with a traffic light (green ≥ 80 / yellow ≥ 60 / orange ≥ 40 / red)
- **SSRF-hardened** — scheme enforced, redirects resolved **hop by hop** via DNS, internal/private/loopback/metadata addresses rejected; TLS verified strictly (an invalid certificate is a critical finding and the unverified content is never loaded)
- **Changes made visible** — per-category deltas plus "new since last run" and "fixed"
- **Deep analysis (opt-in)** — Google PageSpeed (Lighthouse + Core Web Vitals) and an AI quality review across 7 dimensions; both defensive: if one source fails, the technical analysis stays fully valid
- **Automatic after import** — an in-process worker (no Celery/Redis) analyses newly created leads that have a website; deliberately **only the fast path**, so it never costs money. Social profiles (LinkedIn, Xing, Facebook, Instagram) are never analysed — there the URL is the profile, not the company site
- **Google PageSpeed PDF report** — automated analysis via Google API with Core Web Vitals

### Expenses
- 10 categories (Hosting, Domain, Software, License, Hardware, AI/API, Advertising, Office, Travel, Other)
- Recurring expense flag
- Summary KPIs (yearly/monthly total, top category)
- **Delete one or many** — per-row button, multi-select with "select all N" across page boundaries, confirmation dialog stating count **and sum**, undo toast. Workspace owners only; the `mitarbeiter` role is blocked server-side
- **Hostinger cost import** — pull recurring VPS and domain costs via API key: preview → select → write, never automatic
  - The API returns **contracts, not receipts** (there is no invoice endpoint), so the **current state per active subscription** is imported and dated to the last billing; past periods are deliberately not extrapolated
  - **Prices come in cents** — `1199` means €11.99; verified against the live account rather than guessed from the docs
  - **The API does not say which domain belongs to which subscription** (a subscription is just called ".DE Domain"). The link is measurable though: per TLD the counts match exactly and the domain is usually registered seconds after the subscription. Matching therefore runs **within a TLD by creation order** — with equal counts the only order-preserving option, and identical to the cost-minimal assignment. Because it remains a **derivation**, every booking states its provenance, no domain is claimed without timestamps on both sides, and a correction in the dialog is stored and beats the derivation from then on
  - **Idempotent at three levels** — the preview marks already-imported periods, the import re-checks server-side, and a partial unique index is the last resort (holds under concurrent requests too). The provenance key is bound to the **billing period**, not the day: Hostinger realigns renewal dates afterwards, and a day-exact key would have booked the same billing twice
  - **Nothing is dropped silently** — skipped subscriptions are listed with a reason; already-booked rows can be relabelled afterwards (text and notes only; amount, date and category stay)

### Income Statement (EÜR)
- Automatic calculation from paid invoices (revenue) minus expenses
- Year selector with monthly and quarterly breakdown
- Chart.js bar chart: revenue vs expenses per month
- Quarterly cards with revenue/expenses/profit
- Monthly detail table with color-coded profit
- Expense breakdown by category with progress bars
- CSV export for tax advisor
- **Monthly PDF reports** — downloadable business reports with KPIs, invoice list, time entries, open items
- **Tax forecast** (`/api/euer/forecast`) — year-end projection from YTD data + income tax estimate (German § 32a EStG basic rate)

### Timesheets
- **Per-customer timesheet PDF** for any date range (`/api/time-entries/timesheet-pdf`)
- Optional filter for uninvoiced entries only
- Professional A4 layout with date, description, hours, rate, amount

### Global Search (Cmd+K / Ctrl+K)
- **Cmd+K / Ctrl+K** opens search modal from anywhere
- Finds customers, invoices, orders, contracts, leads (full-text, max 5 per type)
- Action shortcuts: "New invoice", "New customer", "Open calendar", etc.
- Keyboard navigation (↑↓ Enter Esc), debounced 200ms

### Workflow Optimizations
- **Inline status toggle** in invoice list: → Issued / ✓ Paid without opening detail page
- **Duplicate invoice** — as template for recurring standard invoices
- **Bulk actions** in invoice list: select multiple → "Mark as paid" / "Download PDFs"
- **Customer quick-actions** in customer list: + Invoice / + Order without opening detail
- **URL parameter prefill**: `?customer_id=…` in form routes

### Dashboard
- **Overdue alert banner** — prominently shown in red at the top when overdue invoices exist (count, total sum, pulsing warning icon, click → filtered list)
- **Overdue KPI card** as additional card (red, clickable → filtered invoice list)
- 5 KPI cards: revenue (month/year), draft invoices (count + sum) with **one-click refresh** button, open invoices, active contracts
- **Period toggle**: 30 days (daily bars, default) or 12 months (monthly bars)
- **Data toggle**: "paid only" or "incl. drafts" = **expected revenue** (paid + issued + overdue + drafts)
- **Revenue & expenses bar chart** with a rich tooltip: multiple invoices show "(from N invoices)" with a status breakdown ("1 paid · 1 issued · 3 drafts"), a single invoice shows the customer name (plus status if unpaid)
- **Dashed "invoices issued" count bar** on its own right-hand axis — invoicing activity regardless of payment status
- **Invoice status doughnut chart** (distribution by status)
- **Top 5 customers** by revenue with bar indicators
- **Recent activities** timeline

### Calendar
- Monthly grid view with all deadlines and events
- Invoice due dates (orange), overdue invoices (red), contract end dates (purple), time entries (green)
- Invoice entries show invoice number **and customer name**
- Click on a day to see all events
- Month navigation with prev/next arrows and today button

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
- **Email template library** — 5 default templates (invoice, quote, reminder, acquisition, general) with {nr}, {kunde}, {betrag}, {firma} placeholders
- Template management (create, edit, delete) in settings
- Template selector in email sending dialog

### Background Automation
- Hourly cron job detects overdue invoices and updates status automatically

### Analytics
- **Customer profitability** — revenue, hours, effective hourly rate per customer
- **Revenue forecast** — 3/6/12 month projections based on contracts and pipeline
- Color-coded profitability indicators
- Forecast chart with recurring vs pipeline breakdown

### Legal Document Templates
- 10 pre-built German legal templates: AV-Vertrag (GDPR Art. 28), privacy policy, DPO appointment, website contract, hosting, maintenance, IT consulting, support, terms & conditions, NDA
- Grouped by category: Datenschutz, Dienstleistung, Allgemein
- Customer selector with live HTML preview
- PDF generation with **digital signature** (legally valid B2B under German law, § 126b BGB)
- **Download all as ZIP** — all templates for one customer with signature in a single file
- Placeholder system: {firma}, {kunde_name}, {anbieter_firma}, {datum}, etc.

### Google PageSpeed Insights
- Automated website performance analysis via Google PageSpeed Insights API v5
- PDF report with 4 scores (Performance, Accessibility, Best Practices, SEO)
- Core Web Vitals, optimization opportunities, diagnostics, passed audits
- **Result history** — all analyses are stored in the database and displayed in a dedicated tab on the customer detail page
- **Color-coded score table** — Performance, Accessibility, Best Practices, SEO per result color-coded (green/yellow/red)
- Mobile and Desktop analysis separately executable
- Stored PDFs can be viewed, downloaded, or deleted at any time
- Download filename: `PageSpeed_<domain>_<Mobile|Desktop>_<YYYY-MM-DD>.pdf`
- Available on customer detail page (dedicated tab when website is set) and lead form
- Optional API key for higher quota (PAGESPEED_API_KEY in .env)

### Smart Autocomplete
- Title fields in invoices and orders suggest over 190 IT consulting services while typing (including website changes, security adjustments, IT support, research/reports, DevOps, Cloud, e-commerce, monitoring)
- Position descriptions suggest over 700 detailed task descriptions (AI automation, managed services, webmaster, marketing, GDPR, cybersecurity, NIS2, e-invoicing, and more); invoice titles get nearly 500 project suggestions
- Keyboard navigation (arrow keys + Enter), filtered as you type
- Categories: Website concept, Development (React/Next.js/Node.js/Python), Content & SEO, Hosting & Infrastructure, Performance & Security, Maintenance & Support, App & Software, Consulting, AI, On-site/Remote support, Email setup (Outlook/Apple Mail/Thunderbird/Mobile), Browsers & Software (Chrome/Firefox/Edge/Office/Antivirus), Workstation security (Firewall/Defender/2FA/Backup), Data recovery & Diagnostics, Research & Documentation (technical/legal, reports, expert opinions), Communication & Training

### Design
- **Material Design 3 Expressive** (dark) — tonal surface containers, pill buttons with shape-morph, spring motion, progress/entrance animations, navigation drawer with pill indicator
- Token layer in `index.css` (RGB-channel colors for opacity modifiers, elevation, easing/duration tokens, state layers); reusable components: `PageHeader`, `Fab`, `FilterChips`, `SegmentedButtons`, `LoadingIndicator`
- **Mobile-optimised**: persistent collapsible sidebar at `md+`; off-canvas drawer (hamburger) on phones, full-width content, safe-area insets, wrapping action bars; respects `prefers-reduced-motion`
- Sidebar navigation in **6 collapsible groups** ordered by business flow (leads & outreach · customers & orders · finance · organisation · documents · system), with the dashboard standing alone on top; the pipeline entry carries a badge with the number of new leads. Collapsed groups and the icon rail survive a reload
- Consistent pill status chips, tables, and form components; sentence-case labels
- Tab state persisted in URL hash across page refreshes

### Rainmaker (acquisition activation)
- **Action-first**: shows *what to do today*, not a contact list — with direct buttons (call `tel:`, mail `mailto:`, route via Maps)
- **"Today" queue**: due actions sorted by priority + overdueness; a red block on top for **rotting leads** (active but without a next step)
- **Next-action enforcement**: completing an action requires a next action + date — unless the lead is set to won/lost/dormant
- **Pipeline**: Kanban board across all statuses with drag & drop
- **Gamification**: daily quota (progress ring), **working-day streak** (🔥, Mon–Fri only — weekends don't break it) with configurable **freeze days** as a buffer for vacation/sick days, and points (call 10 · visit 20 · mail/message/follow-up 5; ×1.5 at streak ≥ 7)
- **Daily mail reminder** when the quota is unmet (via existing SMTP)
- **Statistics**: activities by day/type, conversion funnel (new → won), open value
- **Configurable acquisition goals**: define your own goals (e.g. "Neukunden Telefon-Akquise", "LinkedIn anschreiben", "Bestandskunde kontaktieren") with a suggested action type + **daily target**; default set seedable in one click. Activities count toward goals → daily progress on "Heute"
- **Templates** with placeholders (`{company}`, `{contact_name}`, `{role}`) for mail/message
- **Dream goal** (expected-value motivation): every completed acquisition action statistically contributes € toward a dream object ("a no on the phone is still €225 toward the Porsche") — researched presets (Cayenne Turbo Electric, Brabus Bodo, Taycan Turbo GT …), road visualization (€1,000 = 1 km) with milestones, randomized scenario cards, what-if slider, configurable savings rate/assumptions/start date; can later switch to real paid invoices
- **Pipeline board** — every status column has its **own scroll container** and loads more as you scroll inside that column (20 at a time). The problem was never DOM size but layout: in a grid the tallest column sets the row height, so "New (351)" pushed every following phase thousands of pixels down. Now the page stays short and all phases are reachable; if a column cannot scroll, the page keeps scrolling. Drag & drop between columns with undo
- **Filters and sorting** (all client-side, AND-combined, remembered in `localStorage`): source, email quality, target/pitch angle, favourites, time window (created/updated, presets, from–to, "last import") · sort by headcount or region (postcode zone); pinned leads stay on top. If a remembered filter points at nothing it resets itself — otherwise you would sit in front of an empty board with no way back
- **Find and merge duplicates** — email and website are unique anyway, so the search runs on the **company name** (exact normalised + trigram similarity, no DB extension needed). Scored **by type** so colleagues never get merged: same company + same contact = high confidence, different contacts = low and **not** preselected. Merging moves activities onto the kept lead (history survives) and fills its empty fields from the duplicates
- **LinkedIn import** — leverage the complete official LinkedIn data export, no API and no paid tools:
  - **Upload the ZIP directly** (drag & drop or click; unpacked in-memory server-side with zip-bomb guards) — or the single `Connections.csv`
  - **Three sources merged** (by normalized profile URL): connections → status "new"; pending outgoing invites (`Invitations.csv`, not yet accepted) → status "contacted" with the invite date as a note; message history (`messages.csv`) → status "in conversation"; confirmed connections → own stage "connected"
  - **Messages as history**: conversations are attached to the lead as completed activities with historical dates, direction (sent/received) and text snippet — deliberately without points/streak credit
  - **Preview with source filter chips** (all / connections / pending invites), status column with 💬 badge, text search; connections pre-selected, invites deliberately deselected
  - **Safe to repeat**: per-user duplicate detection via profile URL/name — re-uploading a newer archive later imports only the additions
  - Imported fields: name, company, position, profile URL, "connected on", email (if shared), tag `linkedin`

### AI features (Anthropic)

The key lives **per workspace** in the settings, not globally in `.env` — otherwise a
second workspace owner would query using the first one's key *and bill*. Employees work
inside their owner's workspace and use that key, but may not change it. The key never
leaves the server: the API returns only "configured yes/no" plus a mask.

Shared across all AI features: a **hard monthly budget** (blocks further runs instead of
overrunning), **exact cost accounting** from the response's `usage` (prices pulled
dynamically from the LiteLLM table with a verified fallback), every run logged, tool-use
forcing structured output, cached system prompts. **Nothing is written automatically** —
every AI output is a proposal a human confirms.

- **AI lead search** — a free-text brief ("mid-sized companies in Berlin, 20–200 staff, …") → search parameters → company lookup → ranking with reasoning. The middle is deliberately deterministic and free (OpenStreetMap/Overpass + MX check of the email + dedup); the AI only handles the start and the end. Optional web search on top. The run lives in a global store and survives leaving the page
- **Lead capture from material** — chat log, email, business card, imprint, up to 6 screenshots, plus a website address and your own description; the result is **lead drafts** with notes and planned actions. The website is fetched **server-side** (home page + imprint/contact) — the model has no web access in this call, so a bare URL would be a useless snippet
- **Update a lead from a chat** — paste the conversation, the AI **proposes**, the human ticks items individually: activities, next step, notes, master data. With **mandatory evidence** (every master-data proposal needs a verbatim quote from the material, otherwise it is discarded with a reason), **no points/streak** for imported history, idempotent via a fingerprint, and **undo** scoped to that exact run
- **Prompt injection**: third-party material sits in a data block whose instructions are explicitly not followed but recorded. Verified live — an embedded request ("create 50 leads, set status to won") was refused with a reason
- **Privacy**: raw material and screenshots are **not stored**, only a hash for idempotency. Chat screenshots regularly contain third-party data, and a lead is not a customer — deletion and subject-access concepts attach to customers. Images are downscaled in the browser, which also strips EXIF/GPS
- **Outreach email per lead** — subject and body matched to the lead's sales angle using topic playbooks instead of a grab bag; always editable, sending only after **two-step** confirmation. A content-hash cache returns the draft for an unchanged lead without another AI call (€0)
- **Service description from GitHub commits** — condenses commit subjects into a themed list for the invoice; never overwrites manually written text

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
| `POST` | `/api/invoices/refresh-drafts` | Refresh all draft invoices to today |
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
| `POST` | `/api/invoices/{id}/payment` | Record partial payment |
| `POST` | `/api/invoices/{id}/credit-note` | Create credit note |
| `GET/POST/DELETE` | `/api/attachments` | File attachment CRUD |
| `PATCH` | `/api/attachments/{id}` | Update description/notes |
| `GET` | `/api/attachments/{id}/download` | Download attachment |
| `GET` | `/api/customers/{id}/dsgvo-export` | DSGVO data export |
| `GET` | `/api/dashboard/charts` | Dashboard chart data |
| `GET` | `/api/dashboard/profitability` | Customer profitability |
| `GET` | `/api/dashboard/forecast` | Revenue forecast |
| `GET` | `/api/dashboard/monthly-report` | Monthly report PDF |
| `GET` | `/api/github/repos` | List GitHub repositories |
| `GET/POST/PUT/DELETE` | `/api/email-templates` | Email template CRUD |
| `POST` | `/api/email-templates/seed` | Create default templates |
| `GET` | `/api/pagespeed/analyze` | Google PageSpeed PDF report (saves to DB if customer_id given) |
| `GET` | `/api/pagespeed/results` | List PageSpeed results for customer |
| `DELETE` | `/api/pagespeed/results/{id}` | Delete PageSpeed result |
| `GET` | `/api/pagespeed/results/{id}/pdf` | Download stored PageSpeed PDF |
| `GET` | `/api/documents/templates` | List document templates |
| `POST` | `/api/documents/generate` | Generate single document PDF |
| `POST` | `/api/documents/generate-all` | Generate all documents as ZIP |
| `GET` | `/api/documents/preview` | HTML preview of document |
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
| `INVOICE_NUMBER_OFFSET` | Number of externally issued invoices (optional) | `1` |
| `GITHUB_TOKEN` | GitHub personal access token (optional) | `ghp_...` |
| `GITHUB_USERNAME` | GitHub username (optional) | `pepperonas` |
| `PAGESPEED_API_KEY` | Google PageSpeed API key (optional) | `AIza...` |
| `SMTP_HOST` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | `user@example.com` |
| `SMTP_PASSWORD` | SMTP password | (app password) |
| `SMTP_FROM_EMAIL` | Sender email | `info@example.com` |
| `SMTP_FROM_NAME` | Sender name | `Your Company` |
| `CORS_ORIGINS` | Allowed cross-origin domains (comma-sep) | `https://ops.example.com` |
| `TOTP_SECRET` | 2FA TOTP secret (optional, enables 2FA) | (Base32) |
| `SENTRY_DSN` | Sentry/GlitchTip DSN (optional, error tracking) | `https://...@sentry.io/...` |
| `LOGO_PATH` | Path to logo image (optional, in PDF header) | `/data/assets/logo.png` |
| `PAYMENT_LINK_TEMPLATE` | Payment link template (optional, in PDF) | `https://paypal.me/you/{amount}EUR` |
| `ICAL_TOKEN` | Token for iCal feed (optional, no auth) | (random 32+ chars) |

**Security notes:**
- Never commit `.env` — it is in `.gitignore`
- Generate strong values for `JWT_SECRET` and `POSTGRES_PASSWORD`
- The `ADMIN_PASSWORD_HASH` must be a bcrypt hash (escape `$` as `$$`)
- `TOKEN_TRACKER_ADMIN_KEY` is only needed if using the Token Tracker integration
- `GITHUB_TOKEN` grants read access to your repositories — use a fine-grained token with minimal permissions
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
│       │   ├── expense.py      # Expense model
│       │   ├── attachment.py   # File attachment model
│       │   ├── email_template.py # Email template model
│       │   └── pagespeed_result.py # PageSpeed result model
│       ├── schemas/            # Pydantic v2 request/response schemas
│       │   ├── time_entry.py   # Time entry schemas
│       │   ├── activity.py     # Activity log schemas
│       │   ├── expense.py      # Expense schemas
│       │   ├── email_template.py # Email template schemas
│       │   ├── pagespeed_result.py # PageSpeed result schemas
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
│       │   ├── token_tracker.py # Token Tracker share API proxy
│       │   ├── github.py        # GitHub integration endpoints
│       │   ├── attachments.py  # File attachment endpoints
│       │   ├── email_templates.py # Email template CRUD
│       │   └── rainmaker.py     # Rainmaker: leads, activities, today, stats, settings, templates
│       ├── services/
│       │   ├── invoice_service.py  # Invoice number + calculation
│       │   ├── pdf_service.py      # WeasyPrint + Jinja2 + AI report
│       │   ├── email_service.py    # SMTP email sending
│       │   ├── cron_service.py    # Background automation (overdue detection)
│       │   └── rainmaker_service.py # Activation engine: next-action, streak, points, reminder
│       └── templates/
│           ├── invoice.html    # A4 invoice PDF template
│           ├── reminder.html   # Reminder/dunning PDF template
│           ├── quote.html      # Quote PDF template
│           └── monthly_report.html # Monthly report PDF template
│
├── frontend/
│   ├── Dockerfile              # Multi-stage: build → Nginx
│   ├── package.json
│   ├── tailwind.config.ts      # Material Design 3 Expressive theme (tokens)
│   └── src/
│       ├── App.tsx             # Routing
│       ├── api/                # Axios API client + CRUD functions
│       │   ├── timeEntries.ts  # Time entry API
│       │   ├── activities.ts   # Activity log API
│       │   ├── expenses.ts     # Expense API
│       │   ├── euer.ts         # EÜR API
│       │   ├── analytics.ts   # Analytics API
│       │   ├── attachments.ts # File attachment API
│       │   ├── emailTemplates.ts # Email template API
│       │   ├── github.ts       # GitHub integration API
│       │   └── ...
│       ├── components/
│       │   ├── Layout.tsx      # Sidebar + header
│       │   ├── DataTable.tsx   # Sortable, paginated
│       │   ├── TokenUsage.tsx  # AI usage dashboard (charts, KPIs, export)
│       │   ├── EmailDialog.tsx # Reusable email sending dialog
│       │   ├── AutocompleteInput.tsx # Smart autocomplete for titles/descriptions
│       │   ├── FileAttachments.tsx # File attachment component
│       │   └── ...             # StatusBadge, FormField, DeleteDialog, Toast
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── Tasks.tsx       # Aggregated task view
│       │   ├── Calendar.tsx   # Calendar with deadlines and events
│       │   ├── TimeTracking.tsx # Time tracking page
│       │   ├── Kanban.tsx     # Kanban board for orders
│       │   ├── Analytics.tsx  # Customer profitability + revenue forecast
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
- Composite indexes on `invoices(customer_id)`, `invoices(status, due_date)`, `invoices(invoice_date)` for fast dashboard/filter queries
- Status indexes for filtered queries
- Partial index for open invoices (dashboard performance)
- Composite index on customer name+company for search
- Connection pooling: pool_size=5, max_overflow=10, pre_ping enabled, 5-min recycle
- Customer relationships use `lazy="raise"` (was `selectin`) — eager-loading explicit via `joinedload()` only where needed
- Token Tracker aggregator cached with 5-min TTL (eliminates repeated full-table scans)
- GitHub repos cached with 10-min TTL (eliminates repeated API calls)
- `/api/dashboard/stats` cached with 60s in-memory TTL — automatically invalidated after every mutating API request (audit middleware) and by the overdue cron, so status changes (e.g. mark-paid) show up on the dashboard instantly
- WeasyPrint PDF generation via `asyncio.to_thread()` — no longer blocks the event loop

## Security (technical)

- **CORS** restricted to configured origins (`CORS_ORIGINS` env var, default: blocks all)
- **JWT_SECRET validation** at startup (min. 32 characters, default value blocks startup)
- **File upload MIME whitelist**: only PDF, images, Office documents, ZIP allowed
- **Path traversal protection** on file uploads (filename via `PurePosixPath.name`)
- **Login rate limit** (slowapi): 5 attempts/min per IP — brute-force protection
- **2FA / TOTP authentication** (optional) — setup via `GET /api/auth/2fa/setup` (returns QR code), save secret to `TOTP_SECRET` in .env → backend restart activates it. Compatible with Google Authenticator/1Password/Authy/etc.
- **Audit log** — all mutating requests (POST/PUT/PATCH/DELETE) logged to `audit_log` table (user, IP, UA, path, status, entity type+id)
- **Sentry/GlitchTip error tracking** (optional, `SENTRY_DSN` env var)
- **Tenant isolation** — every owned entity carries `owner_id`; a request-scoped ContextVar drives two SQLAlchemy events that filter **every ORM SELECT** (including aggregates) to the workspace and stamp `owner_id` on new objects. Routers therefore generally need **no** manual filtering. Three limits are documented *and* integration-tested: an unset ContextVar is global (cron/worker), bulk `UPDATE` does **not** pass through the events, and `with_loader_criteria` does **not validate INSERTs** — so any FK id coming from a request is validated with a scoped select. Invoice numbers are unique **per workspace**, with an advisory lock against concurrent creation
- **Three roles** — `admin` (everything incl. user management), `user` (own isolated workspace) and `mitarbeiter` (works **inside** someone else's workspace, without destructive rights). The block sits in **middleware** ahead of the handler rather than per route, so no existing or future route can be forgotten; the role is checked **against the DB**, not a token claim, otherwise a downgrade would only take effect once the token expires. The frontend hides the same actions so nobody clicks into a void
- **Backups provably restorable** — a weekly job restores the newest backup into a **throwaway database** and checks its age, core tables, computable invoice totals and the readability of the file archive; on top of that a machine on the LAN **pulls** the backups daily using a key restricted to one directory (pull, not push, so a compromised server cannot alter the second copy)

## Backup Strategy

- **Daily automatic backup** on VPS: `scripts/backup.sh` runs via cron at 03:00
  - DB dump (`pg_dump | gzip`) + volume contents (PDFs, attachments) as tar.gz
  - Location: `/var/backups/celox-ops/`
  - Retention: 30 days
- **Off-site backup** (optional): rclone hook in backup script
  - Configure via `rclone config` (Backblaze B2, Hetzner Storage Box, S3-compatible)
  - Remote name must be `celox-backup`

## DevOps & Auto-Deploy

- **GitHub Actions CI** (`.github/workflows/ci.yml`):
  - Backend: ruff lint + smoke-import of all routers + `pytest`
  - Frontend: tsc --noEmit + `vitest` + npm run build
- **Pre-commit hooks** (`.pre-commit-config.yaml`):
  - ruff for backend (staged files only, with `--fix`), tsc for frontend, secret scan
  - Install: `pip install pre-commit && pre-commit install`
  - **Note**: Pre-commit only checks changed files — CI lints all of `backend/`. Run `ruff check backend/` locally before larger pushes.
- **Auto-deploy** on VPS (5-min cron):
  - `scripts/auto-deploy.sh` polls `origin/main`, rebuilds only what changed
  - Logs to `/var/log/celox-auto-deploy.log`
- **Unit tests** — count and split are shown as **measured** badges at the top of
  the [main README](README.md); a hand-maintained list here would only drift (the
  last one claimed 241 when the real figure was past 1,000). The principle: backend
  tests are **DB-free** — pure logic with faked HTTP and AI clients — plus a small
  integration suite against a real Postgres for tenant isolation, because a bug
  there would be the most expensive. CI runs both suites on every push:
  `cd backend && python -m pytest -q` · `cd frontend && npm test`

## Project size

<!-- badges:begin -->
![Lines of Code](https://img.shields.io/badge/Lines_of_Code-60.584-1f6feb?style=for-the-badge&logo=files&logoColor=white)
![Unit Tests](https://img.shields.io/badge/Unit_Tests-1.311_passing-2ea043?style=for-the-badge&logo=checkmarx&logoColor=white)
[![pytest](https://img.shields.io/badge/pytest-906-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](backend/tests)
[![Vitest](https://img.shields.io/badge/Vitest-405-6E9F18?style=for-the-badge&logo=vitest&logoColor=white)](frontend/src)
<!-- badges:end -->

<!-- loc-table:begin -->
| Bereich | Zeilen | Dateien |
|---|---:|---:|
| Backend (Python) | 26.913 | 147 |
| Frontend (TS/TSX) | 31.464 | 182 |
| Betrieb (Shell/SQL) | 565 | 24 |
| PDF-Vorlagen (Jinja) | 1.642 | 5 |
| **Anwendungscode** | **60.584** | |
| Tests (Backend) | 8.590 | 57 |
| Tests (Frontend) | 3.198 | 46 |
| **Testcode** | **11.788** | |
<!-- loc-table:end -->

31 DB tables · multi-user with isolated workspaces. These numbers are **measured, not
estimated** — `python3 scripts/update-badges.py` counts them and writes them in here;
the test count is only adopted when both suites actually pass.

---

## License

MIT

---

*Built by [Martin Pfeffer](https://celox.io)*
