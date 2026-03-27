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

---

**Business-Management-Webapp für [celox.io](https://celox.io) IT-Consulting.**

Verwaltet Kunden, Aufträge, Verträge und Rechnungen mit PDF-Generierung. Single-User-Anwendung mit JWT-Authentifizierung. Gesamte UI auf Deutsch.

## Features

- **Kundenverwaltung** — Stammdaten, Kontakte, verknüpfte Aufträge/Verträge/Rechnungen
- **Auftragsverwaltung** — Status-Workflow (Angebot → Beauftragt → In Arbeit → Abgeschlossen)
- **Vertragsverwaltung** — Hosting, Wartung, Support mit automatischer Verlängerung
- **Rechnungen** — Dynamische Positionen, automatische Rechnungsnummern (CO-YYYY-NNNN)
- **PDF-Generierung** — Professionelle Rechnungs-PDFs mit celox.io Branding via WeasyPrint
- **Kleinunternehmerregelung** — Konfigurierbar, beeinflusst Steuerberechnung und PDF
- **Dashboard** — Umsatz-KPIs, offene/überfällige Rechnungen, aktive Verträge
- **Dark Mode UI** — Professionelles dunkles Design mit celox-Blau (#00b4d8)

## Tech Stack

| Layer | Technologie |
|-------|------------|
| Frontend | React 18, TypeScript, TailwindCSS, Vite, Zustand |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| Datenbank | PostgreSQL 16 (async via asyncpg) |
| PDF | WeasyPrint + Jinja2 Templates |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Infra | Docker Compose, Nginx Reverse Proxy |

## Quickstart

```bash
# .env erstellen
cp .env.example .env
# Werte in .env anpassen (insb. Passwörter, JWT_SECRET)

# Starten
docker compose up -d --build

# App unter http://localhost:8090 erreichbar
```

## Development

```bash
docker compose -f docker-compose.dev.yml up -d --build

# Backend: http://localhost:8000 (mit Auto-Reload)
# Frontend: http://localhost:5173 (mit HMR)
# API Docs: http://localhost:8000/docs
```

## Deployment

Gehostet unter **https://ops.celox.io** auf Hostinger VPS (Ubuntu 24.04).

```bash
# Auf VPS deployen
git pull && docker compose up -d --build
```

## Projektstruktur

```
celox-ops/
├── backend/          # FastAPI (Python 3.12)
│   ├── app/
│   │   ├── models/   # SQLAlchemy Models
│   │   ├── schemas/  # Pydantic Schemas
│   │   ├── routers/  # API Endpoints
│   │   ├── services/ # Business Logic + PDF
│   │   └── templates/# Jinja2 Invoice Template
│   └── alembic/      # DB Migrations
├── frontend/         # React 18 + TypeScript
│   └── src/
│       ├── pages/    # Kunden, Aufträge, Verträge, Rechnungen
│       ├── components/# DataTable, StatusBadge, Layout, etc.
│       └── api/      # Axios API Client
├── nginx/            # Reverse Proxy Config
└── docker-compose.yml
```

---

*© 2026 Martin Pfeffer | [celox.io](https://celox.io)*
