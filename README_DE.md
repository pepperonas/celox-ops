<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/← Zurück-README-black?style=flat-square" alt="Zurück"></a>
  &nbsp;
  <a href="README_EN.md"><img src="https://img.shields.io/badge/%F0%9F%87%AC%F0%9F%87%A7-English-black?style=flat-square" alt="English"></a>
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="celox ops" width="1024">
</p>

# celox ops

Gesch&auml;ftsverwaltungs-Webapp f&uuml;r Freelancer und IT-Berater. Verwaltet Kunden, Auftr&auml;ge, Vertr&auml;ge und Rechnungen mit professioneller PDF-Generierung, KI-Nutzungstracking und deutschsprachiger Oberfl&auml;che. Einzelbenutzer-Anwendung mit JWT-Authentifizierung.

---

## Features

### Kundenverwaltung
- Stammdaten (Name, Firma, E-Mail, Telefon, Adresse, Website)
- Uebersicht verknuepfter Auftraege, Vertraege und Rechnungen pro Kunde
- Volltextsuche ueber alle Felder
- Loeschsschutz bei bestehenden Referenzen

### Auftragsverwaltung
- Status-Workflow: **Angebot → Beauftragt → In Arbeit → Abgeschlossen** (oder Storniert)
- Farbcodierte Status-Badges
- Optionale Felder fuer Betrag, Stundensatz und Zeitraum

### Vertragsverwaltung
- Vertragstypen: Hosting, Wartung, Support, Sonstige
- Automatische Verlaengerung mit konfigurierbarer Kuendigungsfrist
- Monatliche Betragserfassung

### Rechnungen
- **Automatisch generierte Rechnungsnummern** im Format `CO-YYYY-NNNN` (fortlaufend pro Jahr)
- **Dynamische Positionen** — Zeilen hinzufuegen/entfernen mit Live-Berechnung
- Netto/MwSt./Brutto automatisch berechnet
- Status-Workflow: Entwurf → Gestellt → Bezahlt (oder Ueberfaellig/Storniert)
- Optionale Verknuepfung mit Auftraegen oder Vertraegen
- **Kleinunternehmerregelung** — konfigurierbar, beeinflusst Berechnung und PDF-Text

### Schnellrechnungen
- Ein-Klick-Erstellung von der Kundendetailseite
- Einzelposition mit Beschreibung und Betrag
- Automatische Rechnungsnummer, 14 Tage Zahlungsziel

### PDF-Generierung
- Professionelle A4-Rechnungs-PDFs mit anpassbarem Branding
- Generiert mit **WeasyPrint** und Jinja2-Templates
- Beinhaltet: Absender, Empfaenger, Positionen, Summen, Bankdaten, Steuerinfo
- Optionaler **KI-Nutzungsbericht** als Anhang mit waehlbarem Zeitraum

### KI-Nutzungstracking (Token Tracker Integration)
- Integration mit [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) ueber sichere Share-API
- **Zeitraumfilter** — 7/30/90 Tage, gesamter Zeitraum oder benutzerdefiniert
- **KPI-Karten**: Kosten, aktive Arbeitszeit, geschriebene Codezeilen, KI-Anfragen
- **Diagramme** (Chart.js): taegliche Arbeitsintensitaet, kumulativer Kostentrend, Code-Entwicklung
- **Sitzungstabelle**: Datum, aktive Dauer, KI-Modell, Anfragen, Codezeilen, Kosten
- **Aktive Zeiterfassung** — misst echte Arbeitszeit (nicht Sitzungsdauer) basierend auf Nachrichtenintervallen mit 5-Minuten-Luecken-Schwellwert
- **CSV-Export** und **HTML-Bericht** zur Weitergabe an Kunden
- Kundenfreundliche Bezeichnungen — "Arbeitssitzungen" statt "Sessions", "Codezeilen" statt "Tokens"
- KI-Nutzungsbericht kann als zweite Seite an **Rechnungs-PDFs angehaengt** werden

### Dashboard
- Umsatz aktueller Monat und Jahr
- Offene Rechnungen (Anzahl + Gesamtbetrag)
- Ueberfaellige Rechnungen (hervorgehoben)
- Aktive Vertraege (Anzahl + monatliche Summe)

### Einstellungen
- Token Tracker Verbindungsstatus
- Konfigurationsanleitung fuer Token Tracker Integration

### Design
- **GitHub-inspiriertes Dark Theme**
- Farbpalette: `#0d1117` (Hintergrund), `#161b22` (Oberflaechen), `#58a6ff` (Akzent)
- Responsives Layout mit einklappbarer Seitenleiste
- Einheitliche Status-Badges, Tabellen und Formular-Komponenten
- Tab-Zustand in URL-Hash ueber Seitenaktualisierungen hinweg gespeichert

---

## Tech Stack

| Schicht | Technologie | Zweck |
|---------|------------|-------|
| **Frontend** | React 18, TypeScript, TailwindCSS | SPA mit typisierten Komponenten |
| **Bundler** | Vite 6 | Schneller Build + HMR |
| **State** | Zustand | Leichtgewichtiger Auth-State |
| **HTTP** | Axios | API-Client mit JWT-Interceptor |
| **Diagramme** | Chart.js + react-chartjs-2 | Interaktive KI-Nutzungsdiagramme |
| **Backend** | Python 3.12, FastAPI | Asynchrone REST-API mit OpenAPI-Docs |
| **Validierung** | Pydantic v2 | Request/Response-Schemas |
| **ORM** | SQLAlchemy 2.0 (async) | Asynchroner Datenbankzugriff |
| **Datenbank** | PostgreSQL 16 | Relationale Speicherung via asyncpg |
| **Migrationen** | Alembic | Schema-Versionierung |
| **PDF** | WeasyPrint + Jinja2 | HTML-zu-PDF Rechnungsgenerierung |
| **Auth** | JWT (python-jose + passlib) | Token-basierte Auth mit bcrypt |
| **Infra** | Docker Compose | Multi-Container-Orchestrierung |
| **Proxy** | Nginx | Reverse Proxy + statische Dateien |

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

## API-Uebersicht

Alle Endpunkte unter `/api/`, geschuetzt via JWT Bearer Token.

| Methode | Endpunkt | Beschreibung |
|---------|----------|-------------|
| `POST` | `/api/auth/login` | Anmeldung (OAuth2-Formular → JWT) |
| `GET` | `/api/auth/me` | Aktueller Benutzer |
| `GET` | `/api/customers` | Kundenliste (Suche, Paginierung, Sortierung) |
| `GET` | `/api/customers/{id}` | Kundendetail mit Referenzanzahl |
| `POST` | `/api/customers` | Kunde anlegen |
| `PUT` | `/api/customers/{id}` | Kunde aktualisieren |
| `DELETE` | `/api/customers/{id}` | Kunde loeschen (mit Referenzpruefung) |
| `GET` | `/api/orders` | Auftragsliste (Filter: Status, Kunde) |
| `POST/PUT/DELETE` | `/api/orders/{id}` | CRUD fuer Auftraege |
| `GET` | `/api/contracts` | Vertragsliste (Filter: Status, Typ) |
| `POST/PUT/DELETE` | `/api/contracts/{id}` | CRUD fuer Vertraege |
| `GET` | `/api/invoices` | Rechnungsliste (Filter: Status, Kunde) |
| `POST` | `/api/invoices` | Rechnung erstellen (auto. Nummer) |
| `POST` | `/api/invoices/quick` | Schnellrechnung (Einzelposition) |
| `PUT` | `/api/invoices/{id}` | Rechnung aktualisieren |
| `PUT` | `/api/invoices/{id}/status` | Status aendern |
| `POST` | `/api/invoices/{id}/generate-pdf` | PDF generieren |
| `GET` | `/api/invoices/{id}/pdf` | PDF herunterladen |
| `DELETE` | `/api/invoices/{id}` | Loeschen (nur Entwuerfe) |
| `GET` | `/api/dashboard/stats` | Dashboard-KPIs |
| `GET` | `/api/token-tracker/projects` | Projekte aus Token Tracker |
| `GET/POST` | `/api/token-tracker/shares` | Share-Tokens verwalten |
| `DELETE` | `/api/token-tracker/shares/{id}` | Share widerrufen |
| `GET` | `/api/health` | Health Check |

Interaktive API-Docs unter `/docs` (Swagger UI).

---

## Schnellstart

### Voraussetzungen
- Docker & Docker Compose
- Git

### Installation

```bash
git clone https://github.com/pepperonas/celox-ops.git
cd OPS

# Umgebung konfigurieren
cp .env.example .env
# .env bearbeiten: Passwoerter, JWT_SECRET, Geschaeftsdaten setzen
# Passwort-Hash generieren:
#   python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('dein-passwort'))"
# $ als $$ in .env fuer Docker Compose escapen

# Starten
docker compose up -d --build

# App erreichbar unter http://localhost:8090
```

### Entwicklung

```bash
docker compose -f docker-compose.dev.yml up -d --build

# Backend:  http://localhost:8000 (Auto-Reload)
# Frontend: http://localhost:5173 (Vite HMR)
# API Docs: http://localhost:8000/docs
# DB:       localhost:5433 (PostgreSQL)
```

---

## Deployment

Konzipiert fuer den Betrieb hinter einem Reverse Proxy mit SSL-Terminierung (z.B. Nginx + Let's Encrypt).

- **Port**: 8090 (Docker) — Proxy auf eigene Domain
- **Datenpersistenz**: Docker Volumes fuer PostgreSQL und PDF-Speicher
- **SSL**: Auf dem Host-Reverse-Proxy konfigurieren

```bash
docker compose up -d --build
```

---

## Besser zusammen: Token Tracker Integration

celox ops und der [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) bilden ein vollstaendiges Consulting-Toolkit. OPS uebernimmt die Geschaeftsseite (Kunden, Rechnungen, Vertraege), waehrend der Token Tracker die KI-Entwicklungsmetriken erfasst (Sitzungen, Tokens, Kosten, Code-Output).

### Was diese Kombination einzigartig macht

Als IT-Berater, der KI-gestuetzt entwickelt, stehen Sie vor einer besonderen Herausforderung: Wie dokumentieren Sie transparent, was die KI geleistet hat und was das gekostet hat? celox ops loest genau dieses Problem. Die Kombination aus Geschaeftsverwaltung und KI-Nutzungstracking schafft eine lueckenlose Kette von der Entwicklungsarbeit bis zur Rechnung — vollautomatisch und nachpruefbar.

### Datenfluss

```
Claude Code → Token Tracker → Share API → celox ops → Kunden-Dashboard + Rechnungs-PDF
```

1. **Claude Code** erzeugt Nutzungsdaten waehrend der KI-gestuetzten Entwicklung
2. **Token Tracker** sammelt und speichert projektbezogene Metriken (Tokens, Kosten, Codezeilen, aktive Zeit)
3. **Share API** bietet sicheren, token-basierten Zugriff auf Projektmetriken
4. **celox ops** zieht Metriken in die Kundendetailseite und rendert interaktive Dashboards
5. **Rechnungs-PDFs** koennen einen KI-Nutzungsbericht als Anhangsseite enthalten

### Vorteile fuer den Berater
- **Transparente Abrechnung** — jede Stunde KI-gestuetzter Arbeit ist mit nachpruefbaren Metriken dokumentiert
- **Automatisiertes Reporting** — kein manuelles Zeittracking oder Berichtschreiben noetig
- **Kundenvertrauen** — Kunden sehen genau, was getan wurde, wie lange es gedauert hat und was es gekostet hat
- **Ein-Klick-Rechnungsstellung** — professionelles PDF mit KI-Bericht in Sekunden generieren

### Vorteile fuer den Kunden
- **Nachpruefbare Arbeitsdokumentation** — sitzungsgenaue Details aller KI-gestuetzten Entwicklung
- **Aktive Zeiterfassung** — echte Arbeitszeit basierend auf Interaktionsmustern, keine aufgeblaehten Sitzungsdauern
- **Kostentransparenz** — KI-Kosten pro Sitzung, pro Tag und kumulative Trends einsehbar
- **Exportierbare Berichte** — CSV- und HTML-Exporte fuer eigene Unterlagen

### Einrichtung

1. **Token Tracker**: Einstellungen → Share API → Admin Key kopieren
2. **celox ops `.env`**: `TOKEN_TRACKER_BASE_URL` und `TOKEN_TRACKER_ADMIN_KEY` setzen
3. **Projekt verknuepfen**: Kunde → Bearbeiten → "Projekt verknuepfen" → Projekt auswaehlen

### Sicherheit

- Share-Tokens: 192-Bit kryptographisch zufaellig (48-Zeichen-Hex)
- Admin Key: 256-Bit, erforderlich fuer Share-Verwaltung
- Oeffentlicher Endpunkt rate-limitiert (30 Req/Min pro IP)
- CORS auf konfigurierte Origins beschraenkt
- Keine Projekt-Enumeration moeglich
- Optionales Ablaufdatum fuer Share-Tokens
- Keine internen Pfade oder Bezeichner exponiert

### Aktive Zeiterfassung

Die aktive Arbeitszeit wird aus Nachrichtenzeitstempeln berechnet: Intervalle zwischen aufeinanderfolgenden KI-Interaktionen werden summiert, wobei Luecken > 5 Minuten als inaktiv zaehlen. Das ergibt realistische Arbeitszeiten (z.B. "5h 15min" statt "194h Sitzungsdauer").

---

## Konfiguration (.env)

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `POSTGRES_USER` | Datenbankbenutzer | `celoxops` |
| `POSTGRES_PASSWORD` | Datenbankpasswort | `sicheres-passwort` |
| `DATABASE_URL` | Asynchroner Connection String | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Token-Signierungsschluessel | (zufaellig, 48+ Zeichen) |
| `ADMIN_USERNAME` | Login-Benutzername | `admin` |
| `ADMIN_PASSWORD_HASH` | bcrypt-Hash des Passworts | `$$2b$$12$$...` |
| `BUSINESS_NAME` | Firmenname (PDFs) | `Ihre Firma` |
| `BUSINESS_OWNER` | Inhabername (PDFs) | `Ihr Name` |
| `BUSINESS_ADDRESS` | Adresse (PDFs) | `Strasse, PLZ Ort` |
| `BUSINESS_EMAIL` | E-Mail (PDFs) | `info@beispiel.de` |
| `BUSINESS_TAX_ID` | USt-IdNr. | `DE...` |
| `BUSINESS_BANK_*` | Bankdaten (IBAN, BIC) | fuer Rechnungs-PDF |
| `KLEINUNTERNEHMER` | Kleinunternehmerregelung | `true` / `false` |
| `PDF_STORAGE_PATH` | PDF-Speicherpfad | `/data/invoices` |
| `TOKEN_TRACKER_BASE_URL` | Token Tracker URL (optional) | `http://host:port` |
| `TOKEN_TRACKER_ADMIN_KEY` | Share Admin Key (optional) | (64-Zeichen-Hex) |

**Sicherheitshinweise:**
- `.env` niemals committen — ist in `.gitignore` eingetragen
- Starke Werte fuer `JWT_SECRET` und `POSTGRES_PASSWORD` generieren
- `ADMIN_PASSWORD_HASH` muss ein bcrypt-Hash sein (`$` als `$$` escapen)
- `TOKEN_TRACKER_ADMIN_KEY` wird nur bei Nutzung der Token Tracker Integration benoetigt

---

## Projektstruktur

```
OPS/
├── docker-compose.yml          # Produktion: DB, Backend, Frontend, Nginx
├── docker-compose.dev.yml      # Entwicklung mit Hot-Reload
├── .env.example                # Umgebungsvariablen-Vorlage
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # Datenbank-Migrationen
│   └── app/
│       ├── main.py             # FastAPI-App, CORS, Lifespan
│       ├── config.py           # Pydantic Settings (env-basiert)
│       ├── database.py         # SQLAlchemy Engine + Async Session
│       ├── auth.py             # JWT-Login, Token-Validierung
│       ├── models/             # SQLAlchemy 2.0 Mapped Models
│       ├── schemas/            # Pydantic v2 Request/Response Schemas
│       ├── routers/            # API-Endpunkte (alle paginiert)
│       │   ├── customers.py    # CRUD + Suche + Referenzpruefung
│       │   ├── orders.py       # CRUD + Status/Kunden-Filter
│       │   ├── contracts.py    # CRUD + Status/Typ-Filter
│       │   ├── invoices.py     # CRUD + PDF + Status + Schnellrechnung
│       │   ├── dashboard.py    # Aggregierte KPIs
│       │   └── token_tracker.py # Token Tracker Share-API-Proxy
│       ├── services/
│       │   ├── invoice_service.py  # Rechnungsnummer + Berechnung
│       │   └── pdf_service.py      # WeasyPrint + Jinja2 + KI-Bericht
│       └── templates/
│           └── invoice.html    # A4-Rechnungs-PDF-Template
│
├── frontend/
│   ├── Dockerfile              # Multi-Stage: Build → Nginx
│   ├── package.json
│   ├── tailwind.config.ts      # Benutzerdefiniertes Dark Theme
│   └── src/
│       ├── App.tsx             # Routing
│       ├── api/                # Axios API-Client + CRUD-Funktionen
│       ├── components/
│       │   ├── Layout.tsx      # Seitenleiste + Header
│       │   ├── DataTable.tsx   # Sortierbar, paginiert
│       │   ├── TokenUsage.tsx  # KI-Nutzungs-Dashboard (Diagramme, KPIs, Export)
│       │   └── ...             # StatusBadge, FormField, DeleteDialog, Toast
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── customers/      # Liste, Formular, Detail
│       │   ├── orders/         # Liste, Formular, Detail
│       │   ├── contracts/      # Liste, Formular, Detail
│       │   └── invoices/       # Liste, Formular, Detail
│       └── utils/
│           ├── formatters.ts   # Datum (DD.MM.YYYY), Waehrung (1.234,56 EUR)
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
│  │     └── Fortlaufende Nummer (nullgepolstert, pro Jahr)
│  └──────── Kalenderjahr
└─────────── Konfigurierbares Praefix
```

---

## Lizenz

MIT

---

*Erstellt von [Martin Pfeffer](https://celox.io)*
