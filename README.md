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
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)](https://alembic.sqlalchemy.org/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![License](https://img.shields.io/badge/License-Private-red)](#)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen)](#)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![Ruff](https://img.shields.io/badge/Linter-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Zustand](https://img.shields.io/badge/Zustand-State-443E38)](https://zustand-demo.pmnd.rs/)
[![Axios](https://img.shields.io/badge/Axios-HTTP-5A29E4?logo=axios&logoColor=white)](https://axios-http.com/)

---

**Business-Management-Webapp für [celox.io](https://celox.io) IT-Consulting.**

Verwaltet Kunden, Aufträge, Verträge und Rechnungen mit professioneller PDF-Generierung. Single-User-Anwendung mit JWT-Authentifizierung. Gesamte UI auf Deutsch.

Live unter **[ops.celox.io](https://ops.celox.io)**.

---

## Features

### Kundenverwaltung
- Stammdaten (Name, Firma, E-Mail, Telefon, Adresse)
- Übersicht verknüpfter Aufträge, Verträge und Rechnungen pro Kunde
- Suchfunktion über alle Felder
- Löschschutz bei bestehenden Referenzen

### Auftragsverwaltung
- Status-Workflow: **Angebot → Beauftragt → In Arbeit → Abgeschlossen** (oder Storniert)
- Farbcodierte Status-Badges
- Verknüpfung mit Kunden und Rechnungen
- Optionale Felder für Betrag, Stundensatz und Zeitraum

### Vertragsverwaltung
- Vertragstypen: Hosting, Wartung, Support, Sonstige
- Automatische Verlängerung mit konfigurierbarer Kündigungsfrist
- Statusverwaltung: Aktiv, Gekündigt, Ausgelaufen
- Monatliche Betragserfassung

### Rechnungen
- **Automatische Rechnungsnummern** im Format `CO-YYYY-NNNN` (fortlaufend pro Kalenderjahr)
- **Dynamische Positionstabelle** — Zeilen hinzufügen/entfernen mit Live-Berechnung
- Jede Position: Beschreibung, Menge, Einheit, Einzelpreis → automatische Gesamtberechnung
- Netto/USt/Brutto wird live berechnet
- Status-Workflow: Entwurf → Gestellt → Bezahlt (oder Überfällig/Storniert)
- Optionale Verknüpfung mit Aufträgen oder Verträgen

### PDF-Generierung
- Professionelle A4-Rechnungs-PDFs mit celox.io Branding
- Generiert via **WeasyPrint** mit Jinja2-Templates
- Enthält: Absender, Empfänger, Positionstabelle, Summenblock, Bankverbindung
- **Kleinunternehmerregelung** — Konfigurierbar via `.env`, setzt USt auf 0% und zeigt §19-Hinweis
- PDF-Download direkt aus der App

### Dashboard
- Umsatz aktueller Monat und Jahr (Summe bezahlter Rechnungen)
- Offene Rechnungen (Anzahl + Gesamtsumme)
- Überfällige Rechnungen (rot hervorgehoben)
- Aktive Verträge (Anzahl + monatliche Summe)
- KPI-Karten mit farbcodierten Werten

### Design
- **GitHub-inspiriertes Dark Theme** mit professioneller Farbgebung
- Farbpalette: `#0d1117` (Hintergrund), `#161b22` (Oberflächen), `#58a6ff` (Akzent)
- Responsive Layout mit kollabierbarer Sidebar
- Konsistente Status-Badges, Tabellen und Formular-Komponenten
- Tabular-Nums für Zahlen, Uppercase-Labels, dezente Hover-Effekte

---

## Tech Stack

| Schicht | Technologie | Zweck |
|---------|------------|-------|
| **Frontend** | React 18, TypeScript, TailwindCSS | SPA mit typsicheren Komponenten |
| **Bundler** | Vite 6 | Schneller Build + HMR für Entwicklung |
| **State** | Zustand | Leichtgewichtiges Auth-State-Management |
| **HTTP** | Axios | API-Client mit JWT-Interceptor |
| **Backend** | Python 3.12, FastAPI | Async REST-API mit automatischer OpenAPI-Doku |
| **Validierung** | Pydantic v2 | Request/Response-Schemas mit Typ-Sicherheit |
| **ORM** | SQLAlchemy 2.0 (async) | Async-Datenbankzugriff mit Mapped-Typen |
| **Datenbank** | PostgreSQL 16 | Relationale Datenspeicherung via asyncpg |
| **Migration** | Alembic | Datenbank-Schemaversionierung |
| **PDF** | WeasyPrint + Jinja2 | HTML-zu-PDF-Konvertierung für Rechnungen |
| **Auth** | JWT (python-jose + passlib) | Token-basierte Authentifizierung mit bcrypt |
| **Infra** | Docker Compose | Multi-Container-Orchestrierung |
| **Proxy** | Nginx | Reverse Proxy + SSL Termination |

---

## Datenmodell

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
│ notes        │     │ end_date     │     │ status       │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐
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
                     └──────────────┘
```

---

## API-Übersicht

Alle Endpunkte unter `/api/`, geschützt via JWT Bearer Token.

| Methode | Endpunkt | Beschreibung |
|---------|----------|-------------|
| `POST` | `/api/auth/login` | Login (OAuth2 Formular → JWT) |
| `GET` | `/api/auth/me` | Aktueller Benutzer |
| `GET` | `/api/customers` | Kundenliste (Suche, Paginierung, Sortierung) |
| `GET` | `/api/customers/{id}` | Kundendetail mit Referenz-Zähler |
| `POST` | `/api/customers` | Kunde erstellen |
| `PUT` | `/api/customers/{id}` | Kunde aktualisieren |
| `DELETE` | `/api/customers/{id}` | Kunde löschen (mit Referenzprüfung) |
| `GET` | `/api/orders` | Auftragsliste (Filter: Status, Kunde) |
| `POST/PUT/DELETE` | `/api/orders/{id}` | CRUD für Aufträge |
| `GET` | `/api/contracts` | Vertragsliste (Filter: Status, Typ) |
| `POST/PUT/DELETE` | `/api/contracts/{id}` | CRUD für Verträge |
| `GET` | `/api/invoices` | Rechnungsliste (Filter: Status, Kunde) |
| `POST` | `/api/invoices` | Rechnung erstellen (auto Rechnungsnr.) |
| `PUT` | `/api/invoices/{id}` | Rechnung aktualisieren |
| `PUT` | `/api/invoices/{id}/status` | Status ändern |
| `POST` | `/api/invoices/{id}/generate-pdf` | PDF generieren |
| `GET` | `/api/invoices/{id}/pdf` | PDF herunterladen |
| `DELETE` | `/api/invoices/{id}` | Löschen (nur Entwürfe) |
| `GET` | `/api/dashboard/stats` | Dashboard-KPIs |
| `GET` | `/api/health` | Health Check |

Interaktive API-Dokumentation unter `/docs` (Swagger UI).

---

## Quickstart

### Voraussetzungen
- Docker & Docker Compose
- Git

### Installation

```bash
# Repository klonen
git clone https://github.com/pepperonas/celox-ops.git
cd celox-ops

# Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten: Passwörter, JWT_SECRET, Geschäftsdaten anpassen

# Starten
docker compose up -d --build

# App unter http://localhost:8090 erreichbar
```

### Passwort-Hash generieren

```bash
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('dein-passwort'))"
# Ergebnis in .env als ADMIN_PASSWORD_HASH eintragen ($ mit $$ escapen für Docker Compose)
```

---

## Development

```bash
docker compose -f docker-compose.dev.yml up -d --build

# Backend:  http://localhost:8000 (mit Auto-Reload)
# Frontend: http://localhost:5173 (mit Vite HMR)
# API Docs: http://localhost:8000/docs
# DB:       localhost:5433 (PostgreSQL)
```

---

## Deployment

Gehostet unter **https://ops.celox.io** auf Hostinger KVM 4 VPS (Ubuntu 24.04).

- **Port**: 8090 (Docker) → Nginx Reverse Proxy auf dem Host
- **SSL**: Let's Encrypt via Certbot (automatische Erneuerung)
- **Daten-Persistenz**: Docker Volumes für PostgreSQL und PDF-Storage

```bash
# Auf dem VPS
cd /opt/celox-ops
docker compose up -d --build
```

---

## Konfiguration (.env)

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `POSTGRES_USER` | Datenbankbenutzer | `celoxops` |
| `POSTGRES_PASSWORD` | Datenbankpasswort | `sicheres-passwort` |
| `DATABASE_URL` | Async DB-Verbindungsstring | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Geheimschlüssel für Token-Signierung | `zufällig-generiert` |
| `ADMIN_USERNAME` | Login-Benutzername | `martin` |
| `ADMIN_PASSWORD_HASH` | bcrypt-Hash des Passworts | `$$2b$$12$$...` |
| `BUSINESS_NAME` | Firmenname für PDFs | `celox.io — IT-Consulting` |
| `BUSINESS_OWNER` | Inhaber | `Martin Pfeffer` |
| `BUSINESS_ADDRESS` | Geschäftsadresse | `Straße, PLZ Ort` |
| `BUSINESS_TAX_ID` | USt-IdNr. | `DE...` |
| `BUSINESS_BANK_*` | Bankverbindung (IBAN, BIC, Name) | für Rechnungs-PDF |
| `KLEINUNTERNEHMER` | §19 UStG aktiv | `true` / `false` |
| `PDF_STORAGE_PATH` | Speicherpfad für PDFs | `/data/invoices` |

---

## Projektstruktur

```
celox-ops/
├── docker-compose.yml          # Produktion: db, backend, frontend, nginx
├── docker-compose.dev.yml      # Entwicklung mit Hot-Reload
├── .env.example                # Vorlage für Umgebungsvariablen
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # Datenbank-Migrationen
│   │   ├── env.py
│   │   └── versions/
│   └── app/
│       ├── main.py             # FastAPI-App, CORS, Lifespan
│       ├── config.py           # Pydantic Settings (env-basiert)
│       ├── database.py         # SQLAlchemy Engine + async Session
│       ├── auth.py             # JWT-Login, Token-Validierung
│       ├── models/             # SQLAlchemy 2.0 Mapped Models
│       │   ├── customer.py     # + Base (DeclarativeBase)
│       │   ├── order.py        # OrderStatus Enum
│       │   ├── contract.py     # ContractType + ContractStatus Enums
│       │   └── invoice.py      # InvoiceStatus Enum, JSONB Positionen
│       ├── schemas/            # Pydantic v2 Request/Response Schemas
│       │   ├── customer.py     # Base, Create, Update, Response, Detail
│       │   ├── order.py
│       │   ├── contract.py
│       │   └── invoice.py      # + InvoicePosition, InvoiceStatusUpdate
│       ├── routers/            # API-Endpunkte (alle mit Paginierung)
│       │   ├── customers.py    # CRUD + Suche + Referenzprüfung
│       │   ├── orders.py       # CRUD + Status/Kunde-Filter
│       │   ├── contracts.py    # CRUD + Status/Typ-Filter
│       │   ├── invoices.py     # CRUD + PDF + Statusänderung
│       │   └── dashboard.py    # Aggregierte KPIs
│       ├── services/
│       │   ├── invoice_service.py  # Rechnungsnummer + Berechnung
│       │   └── pdf_service.py      # WeasyPrint + Jinja2
│       └── templates/
│           └── invoice.html    # A4 Rechnungs-PDF-Template
│
├── frontend/
│   ├── Dockerfile              # Multi-Stage: Build → Nginx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts      # Custom Theme (Dark, GitHub-Stil)
│   └── src/
│       ├── main.tsx            # React-Einstiegspunkt
│       ├── index.css           # Globale Styles + CSS-Variablen
│       ├── App.tsx             # Routing (react-router-dom v7)
│       ├── types/index.ts      # TypeScript-Interfaces
│       ├── store/authStore.ts  # Zustand Auth-State
│       ├── api/                # Axios API-Client + CRUD-Funktionen
│       │   ├── client.ts       # JWT-Interceptor, 401-Redirect
│       │   ├── customers.ts
│       │   ├── orders.ts
│       │   ├── contracts.ts
│       │   └── invoices.ts
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   └── useCrud.ts      # Generischer CRUD-Hook
│       ├── components/
│       │   ├── Layout.tsx      # Sidebar + Header + Content
│       │   ├── DataTable.tsx   # Sortierbar, paginiert
│       │   ├── StatusBadge.tsx # Farbcodierte Badges
│       │   ├── FormField.tsx   # Wiederverwendbarer Formular-Baustein
│       │   ├── DeleteDialog.tsx
│       │   ├── Toast.tsx
│       │   └── ProtectedRoute.tsx
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── customers/      # Liste, Formular, Detail
│       │   ├── orders/         # Liste, Formular, Detail
│       │   ├── contracts/      # Liste, Formular, Detail
│       │   └── invoices/       # Liste, Formular, Detail
│       └── utils/
│           ├── formatters.ts   # Datum (DD.MM.YYYY), Währung (1.234,56 €)
│           └── validators.ts
│
└── nginx/
    └── default.conf            # /api → Backend, / → Frontend
```

---

## Rechnungsnummer-Format

```
CO-2026-0001
│  │     │
│  │     └── Fortlaufende Nummer (zero-padded, pro Jahr)
│  └──────── Kalenderjahr
└─────────── celox ops Präfix
```

Die nächste freie Nummer wird automatisch ermittelt (höchste bestehende Nummer des Jahres + 1).

---

## Formatierung

| Typ | Format | Beispiel |
|-----|--------|---------|
| Datum | DD.MM.YYYY | 27.03.2026 |
| Datum + Zeit | DD.MM.YYYY HH:mm | 27.03.2026 14:30 |
| Währung | deutsches EUR-Format | 1.234,56 € |
| Dezimaltrenner | Komma (Anzeige), Punkt (DB) | 19,00% / 19.00 |

---

*© 2026 Martin Pfeffer | [celox.io](https://celox.io)*
