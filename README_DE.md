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
- Übersicht verknüpfter Aufträge, Verträge und Rechnungen pro Kunde
- Volltextsuche über alle Felder
- Löschschutz bei bestehenden Referenzen
- **Dokumentenverwaltung** — eigener Tab pro Kunde für Datei-Uploads (Drag & Drop, max. 20 MB), mit Beschreibung und Notizen, nachträglich editierbar
- **DSGVO-Datenexport** — Ein-Klick-Export aller Kundendaten (Art. 15 DSGVO)
- **Google PageSpeed Insights** — Ein-Klick PDF-Report mit Performance, Barrierefreiheit, SEO Scores

### Auftragsverwaltung
- Status-Workflow: **Angebot → Beauftragt → In Arbeit → Abgeschlossen** (oder Storniert)
- Farbcodierte Status-Badges
- Optionale Felder für Betrag, Stundensatz und Zeitraum
- **Angebots-PDF** für Aufträge im Status 'Angebot' mit Positionstabelle und Gültigkeitsdatum
- Optionale Positionstabelle mit dynamischen Zeilen
- Angebots-PDFs herunterladen und per E-Mail versenden

### Kanban-Board
- Visuelle Auftragsverwaltung mit 4 Spalten: Angebot → Beauftragt → In Arbeit → Abgeschlossen
- Drag & Drop zum Statuswechsel
- Karten zeigen Titel, Kunde, Betrag, Datum
- Farbcodierte Spaltenköpfe

### Vertragsverwaltung
- Vertragstypen: Hosting, Wartung, Support, Sonstige
- Automatische Verlängerung mit konfigurierbarer Kündigungsfrist
- Konfigurierbarer Zahlungsturnus (monatlich, quartalsweise, halbjährlich, jährlich)
- Monatliche Betragserfassung

### Rechnungen
- **Automatisch generierte Rechnungsnummern** im Format `CO-YYYY-NNNN` (fortlaufend pro Jahr)
- **Dynamische Positionen** — Zeilen hinzufügen/entfernen (auch die letzte) mit Live-Berechnung
- Netto/MwSt./Brutto automatisch berechnet
- Status-Workflow: Entwurf → Gestellt → Bezahlt (oder Überfällig/Storniert)
- Optionale Verknüpfung mit Aufträgen oder Verträgen
- **Kleinunternehmerregelung** — konfigurierbar, beeinflusst Berechnung und PDF-Text
- **Teilzahlungen** — Zahlungen erfassen, automatisch abgeschlossen bei Vollzahlung
- **Gutschriften** — eigener Nummernkreis GS-YYYY-NNNN, verknüpft mit Originalrechnung
- **Rabattfunktion** — prozentual oder Festbetrag mit Autovervollständigung für Begründungen (Treuerabatt, Erstkundenrabatt, Mengenrabatt, Non-Profit, etc.)
- Rabatt als negative Position auf dem Rechnungs-PDF
- **Sondervereinbarungen** — beliebig viele pro Rechnung mit Autovervollständigung (Hosting, Support, SSL, Migrationen, Zahlungspläne, etc.)
- **Multi-Projekt-Abrechnung** — Token-Tracker-Projekte und GitHub-Repos pro Rechnung über Checkboxen auswählen
- **Aktivitätsdiagramm als Anlage** — optionales CSS-Balkendiagramm der täglichen Arbeitsintensität im PDF
- **Rechnungsnummer-Offset** — konfigurierbar für extern vergebene Rechnungen (INVOICE_NUMBER_OFFSET in .env)
- **Lückenlose Nummerierung** — gelöschte Entwürfe geben ihre Nummer zur Wiederverwendung frei (erste freie Lücke ab Offset+1)
- **Wertorientierte Positionen** — KI-Import verwendet den Rechnungstitel als Positionsbeschreibung statt technischer KI-Begriffe
- **Leistungsbeschreibung** — optionales Freitext-Feld, wird im PDF vor den Positionen angezeigt (Ergebnis statt Tools)
- **Vollständige Zustandsspeicherung** — alle Toggles, Zeiträume, Projektauswahl und Rabatte beim Bearbeiten wiederhergestellt
- **Einheitlicher Zeitraum** — GitHub Commits und Aktivitätsdiagramm übernehmen den Zeitraum vom KI-Nutzungsbericht
- **Ein-Klick-Entwurf-Aktualisierung** — alle Entwürfe auf heute aktualisieren: Rechnungsdatum + Zahlungsziel setzen, KI-Zeit reimportieren (alte Auto-Positionen werden ersetzt, manuelle bleiben erhalten), Summen neuberechnen, PDFs regenerieren
- **USt-Steuerung pro Rechnung** — Checkbox für USt inkl./exkl. (Kleinunternehmerregelung pro Rechnung, nicht nur global)
- **Vollständige Detailansicht** — Rechnungsdetailseite zeigt Rabatt (Zwischensumme, Abzug, Grund), Sondervereinbarungen, Leistungsbeschreibung und Steuerbefreiungshinweis
- **Automatische PDF-Regeneration** — bei jeder Bearbeitung wird ein vorhandenes PDF automatisch neu erstellt, damit Änderungen sofort sichtbar sind

### Schnellrechnungen
- Ein-Klick-Erstellung von der Kundendetailseite
- Einzelposition mit Beschreibung und Betrag
- Automatische Rechnungsnummer, 14 Tage Zahlungsziel
- Autovervollständigung bei Beschreibung (>220 Tätigkeitsvorschläge)
- Komma-Eingabe bei Menge und Einzelpreis (mobil mit Dezimal-Keyboard)

### Wiederkehrende Rechnungen
- Automatische Entwurfserstellung aus aktiven Verträgen basierend auf Zahlungsturnus
- Berechnet Fälligkeit aus Turnus + letztem Rechnungsdatum
- Deutsche Periodenlabel (März 2026, Q1 2026, 1. Halbjahr 2026)
- Ein-Klick-Generierung über die Aufgabenseite
- Beträge aus Monatsbetrag × Turnus-Multiplikator

### KI-Arbeitszeit importieren
- Aktive KI-Arbeitszeit und API-Kosten direkt als Rechnungspositionen importieren
- Konfigurierbarer Stundensatz (Standard 95 €/h)
- Wählbarer Zeitraum für den Import
- Erstellt automatisch zwei Positionen: Arbeitsstunden × Satz + API-Kosten pauschal
- Nur sichtbar wenn Kunde Token Tracker verknüpft hat
- Setzt automatisch den Zeitraum für den KI-Nutzungsbericht-Anhang

### Mahnwesen
- Dreistufiges Mahnsystem: Zahlungserinnerung → 1. Mahnung → Letzte Mahnung
- Professionelle PDF-Vorlagen mit stufenabhängigem Text
- Mahnstufen-Tracking auf jeder Rechnung
- Mahnungs-PDFs generieren und herunterladen
- Mahnungen direkt per E-Mail aus der App versenden

### Zeiterfassung
- Start/Stop-Timer mit Kundenzuordnung (in localStorage gespeichert)
- Manuelle Zeiteinträge mit Datum, Stunden, Stundensatz, Beschreibung
- Zusammenfassung pro Kunde: offene Stunden, Gesamtbetrag, nicht abgerechnete Einträge
- Filter nach Kunde und Zeitraum
- Erfassung abrechenbarer Stunden für Nicht-KI-Arbeit (Meetings, Anrufe, Konfiguration)

### PDF-Generierung
- Professionelle A4-Rechnungs-PDFs mit anpassbarem Branding
- Generiert mit **WeasyPrint** und Jinja2-Templates
- Beinhaltet: Absender, Empfänger, Positionen, Summen, Bankdaten, Steuerinfo
- **Unterschrift** als eingebettetes Bild (Base64, konfigurierbarer Pfad)
- **Zahlungsoptionen**: Banküberweisung (IBAN/BIC) und PayPal (konfigurierbar)
- **Steuernummer** im Footer (gemäß § 14 Abs. 4 UStG)
- Bis zu 3 optionale PDF-Anlagen: KI-Nutzungsbericht, GitHub-Commit-Verlauf, oder beides — jeweils mit unabhängigem Zeitraum
- **PDF-Anzeige im Browser** — Rechnungen, Angebote und Mahnungen direkt in neuem Tab anzeigen
- Standard-Zeitraum für KI-Nutzungsbericht: 1. des Monats bis heute

### E-Mail-Versand
- Rechnungen, Angebote und Mahnungen direkt per SMTP versenden
- Konfigurierbare SMTP-Einstellungen (Host, Port, TLS, Zugangsdaten)
- **Automatische SSL/TLS-Erkennung** — Port 465 (SMTPS, implicit SSL) und Port 587 (STARTTLS) werden automatisch unterschieden
- **CC + BCC Empfänger** im E-Mail-Dialog (Mehrfacheingabe per Komma/Semikolon, einblendbar via "+ CC / BCC")
- Vorgefüllte Empfänger, Betreff und Nachrichtenvorlagen
- Wiederverwendbarer E-Mail-Dialog mit bearbeitbaren Feldern
- PDF wird automatisch angehängt

### Kontakthistorie
- Kunden-Timeline aller Interaktionen
- Automatische Protokollierung: Rechnung erstellt, Mahnung gesendet, E-Mail versendet, Auftrag/Vertrag erstellt
- Manuelle Einträge: Notizen, Anrufe, E-Mails, Meetings
- Farbcodiert nach Typ mit relativen Zeitangaben
- Neuer Tab auf der Kundendetailseite

### KI-Nutzungstracking (Token Tracker Integration)
- Integration mit [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) über sichere Share-API
- **Multi-Projekt-Verknüpfung** — mehrere Token Tracker Projekte pro Kunde, Daten werden automatisch projektübergreifend zusammengeführt
- **Labels bei Verknüpfung gespeichert** — Projektlabels werden beim Verknüpfen erfasst, keine zusätzlichen API-Aufrufe nötig
- **Zeitraumfilter** — 7/30/90 Tage, gesamter Zeitraum oder benutzerdefiniert
- **KPI-Karten**: Kosten, aktive Arbeitszeit, geschriebene Codezeilen, KI-Anfragen
- **Diagramme** (Chart.js): tägliche Arbeitsintensität, kumulativer Kostentrend, Code-Entwicklung
- **Sitzungstabelle**: Datum, aktive Dauer, KI-Modell, Anfragen, Codezeilen, Kosten
- **Aktive Zeiterfassung** — misst echte Arbeitszeit (nicht Sitzungsdauer) basierend auf Nachrichtenintervallen mit 5-Minuten-Lücken-Schwellwert; Intervalle zwischen aufeinanderfolgenden KI-Interaktionen werden summiert, Lücken > 5 Minuten zählen als inaktiv
- **CSV-Export** und **HTML-Bericht** zur Weitergabe an Kunden
- Kundenfreundliche Bezeichnungen — "Arbeitssitzungen" statt "Sessions", "Codezeilen" statt "Tokens"
- KI-Nutzungsbericht kann als zweite Seite an **Rechnungs-PDFs angehängt** werden

### GitHub-Integration
- **Repository-Verknüpfung** — GitHub-Repos über durchsuchbaren Picker mit Kunden verknüpfen (lädt alle Repos via GitHub API)
- **Commit-Verlauf im Rechnungs-PDF** — eigener Toggle mit unabhängigem Zeitraum
- Commits als Anlage 'Entwicklungsprotokoll': Datum, Repository, Commit-Nachricht, Autor
- Kann zusammen mit oder unabhängig vom KI-Nutzungsbericht verwendet werden
- Private Repos unterstützt (erfordert GitHub-Token)

### Leads (Vorgemerkt)
- Potenzielle Kunden und Websites für Akquise vormerken
- Einfache Liste mit URL (Pflicht), Name, Firma, E-Mail, Telefon, Notizen und Status-Workflow (Neu → Kontaktiert → Interessiert → Abgelehnt)
- Volltextsuche über alle Felder
- Integrierte Website-Qualitätsanalyse (SSL, Ladezeit, Mobile, SEO, Barrierefreiheit, Sicherheits-Header)
- Score 0-100% mit farbcodiertem Fortschrittsbalken
- Befunde gruppiert nach Kategorie mit Schweregrad
- Gesprächsargumente-Panel für Akquise-Anrufe
- **Google PageSpeed PDF-Report** — automatische Analyse via Google API mit Core Web Vitals

### Ausgaben
- 10 Kategorien (Hosting, Domain, Software, Lizenz, Hardware, KI/API, Werbung, Büro, Reise, Sonstige)
- Wiederkehrend-Kennzeichen
- Zusammenfassungs-KPIs (Jahres-/Monatstotal, Top-Kategorie)

### EÜR (Einnahmen-Überschuss-Rechnung)
- Automatische Berechnung aus bezahlten Rechnungen (Einnahmen) minus Ausgaben
- Jahresauswahl mit Monats- und Quartalsaufschlüsselung
- Chart.js-Balkendiagramm: Einnahmen vs. Ausgaben pro Monat
- Quartalskarten mit Einnahmen/Ausgaben/Gewinn
- Monatliche Detailtabelle mit farbcodiertem Gewinn
- Ausgabenaufschlüsselung nach Kategorie mit Fortschrittsbalken
- CSV-Export für Steuerberater
- **Monatsberichte als PDF** — herunterladbare Geschäftsberichte mit KPIs, Rechnungsliste, Zeitauswertung, offene Posten

### Dashboard
- **Überfälligkeits-Banner** — prominent rot hervorgehoben am oberen Rand wenn überfällige Rechnungen existieren (mit Anzahl, Gesamtsumme, Pulsierendem Warn-Icon, Klick → gefilterte Liste)
- **Überfällig-Karte** als zusätzliche KPI-Karte (rot, klickbar → gefilterte Rechnungsliste)
- 5 KPI-Karten: Umsatz (Monat/Jahr), Entwürfe (Anzahl + Summe) mit **Ein-Klick-Aktualisierung**, offene Rechnungen, aktive Verträge
- **Zeitraum-Umschalter**: 30 Tage (tägliche Balken, Standard) oder 12 Monate (monatlich)
- **Daten-Umschalter**: nur bezahlte Rechnungen oder inklusive Entwürfe
- **Umsatz- und Ausgaben-Balkendiagramm** (letzte 12 Monate)
- **Rechnungsstatus-Kreisdiagramm** (Verteilung nach Status)
- **Top 5 Kunden** nach Umsatz mit Balkenindikatoren
- **Letzte Aktivitäten** Timeline

### Kalender
- Monatsraster mit allen Fristen und Terminen
- Fällige Rechnungen (orange), überfällige (rot), Vertragsenden (lila), Zeiteinträge (grün)
- Rechnungseinträge zeigen Rechnungsnummer **und Kundennamen**
- Klick auf einen Tag zeigt alle Ereignisse
- Monatsnavigation mit Pfeilen und Heute-Button

### Aufgaben
- Aggregierte Aufgabenliste anstehender Aktionen
- Überfällige Rechnungen (kritische Priorität)
- Rechnungen fällig innerhalb 30 Tagen
- Rechnungsentwürfe noch nicht gestellt
- Verträge laufen innerhalb 60 Tagen aus
- Aktive Aufträge in Bearbeitung
- Farbcodiert nach Priorität (kritisch/Warnung/Info)
- Klick führt zur jeweiligen Detailseite

### Einstellungen
- Token Tracker Verbindungsstatus
- Konfigurationsanleitung für Token Tracker Integration
- **Datenbank-Backup** — Ein-Klick-Export aller Daten (Kunden, Aufträge, Verträge, Rechnungen, Leads, Zeiteinträge, Ausgaben, Aktivitäten) als JSON-Datei
- PDFs als Base64 im Backup enthalten — alles in einer einzigen Datei
- **E-Mail-Vorlagen** — 5 Standardvorlagen (Rechnung, Angebot, Mahnung, Akquise, Allgemein) mit {nr}, {kunde}, {betrag}, {firma} Platzhaltern
- Vorlagenverwaltung (erstellen, bearbeiten, löschen) in Einstellungen
- Vorlagenauswahl im E-Mail-Versand-Dialog

### Hintergrund-Automatisierung
- Stündlicher Cron-Job erkennt überfällige Rechnungen und aktualisiert Status automatisch

### Analyse
- **Kunden-Rentabilität** — Umsatz, Stunden, effektiver Stundensatz pro Kunde
- **Umsatzprognose** — 3/6/12 Monate basierend auf Verträgen und Pipeline
- Farbcodierte Rentabilitätsindikatoren
- Prognosediagramm mit Aufteilung wiederkehrend vs. Pipeline

### Vertragsdokumente
- 10 vordefinierte deutsche Rechtsvorlagen: AV-Vertrag (DSGVO Art. 28), Datenschutzerklärung, DSB-Bestellung, Website-Vertrag, Hosting, Wartung, IT-Beratung, Support, AGB, NDA
- Gruppiert nach Kategorie: Datenschutz, Dienstleistung, Allgemein
- Kundenauswahl mit Live-HTML-Vorschau
- PDF-Generierung mit **digitaler Signatur** (B2B rechtsgültig nach § 126b BGB)
- **Alle als ZIP herunterladen** — alle Vorlagen für einen Kunden mit Unterschrift in einer Datei
- Platzhaltersystem: {firma}, {kunde_name}, {anbieter_firma}, {datum}, etc.

### Google PageSpeed Insights
- Automatische Website-Performance-Analyse via Google PageSpeed Insights API v5
- PDF-Report mit 4 Scores (Performance, Barrierefreiheit, Best Practices, SEO)
- Core Web Vitals, Optimierungsmöglichkeiten, Diagnosen, bestandene Prüfungen
- **Ergebnis-Historie** — alle Analysen werden in der Datenbank gespeichert und im eigenen Tab auf der Kundendetailseite angezeigt
- **Tabelle mit Farbcodes** — Performance, Barrierefreiheit, Best Practices, SEO pro Ergebnis farbcodiert (grün/gelb/rot)
- Mobile und Desktop Analyse separat ausführbar
- Gespeicherte PDFs jederzeit erneut abrufbar (Anzeigen + Herunterladen) oder löschbar
- Download-Dateiname: `PageSpeed_<domain>_<Mobile|Desktop>_<YYYY-MM-DD>.pdf`
- Verfügbar auf Kundendetailseite (eigener Tab bei hinterlegter Website) und Lead-Formular
- Optionaler API-Key für höheres Kontingent (PAGESPEED_API_KEY in .env)

### Intelligente Autovervollständigung
- Titelfelder in Rechnungen und Aufträgen schlagen über 190 IT-Consulting-Leistungen während der Eingabe vor (inkl. Website-Änderungen, Sicherheits-Anpassungen, IT-Betreuung, Recherche/Reports, DevOps, Cloud, E-Commerce, Monitoring)
- Positionsbeschreibungen schlagen über 220 detaillierte Tätigkeitsbeschreibungen vor
- Tastaturnavigation (Pfeiltasten + Enter), gefiltert während der Eingabe
- Kategorien: Website-Konzeption, Entwicklung (React/Next.js/Node.js/Python), Content & SEO, Hosting & Infrastruktur, Performance & Sicherheit, Wartung & Support, App & Software, Beratung, KI, Vor-Ort/Remote-Support, E-Mail-Konfiguration (Outlook/Apple Mail/Thunderbird/Mobile), Browser & Software (Chrome/Firefox/Edge/Office/Antivirus), Sicherheit am Kundenrechner (Firewall/Defender/2FA/Backup), Datenrettung & Fehlerdiagnose, Recherche & Dokumentation (techn./rechtl., Reports, Gutachten), Kommunikation & Schulung

### Design
- **GitHub-inspiriertes Dark Theme**
- Farbpalette: `#0d1117` (Hintergrund), `#161b22` (Oberflächen), `#58a6ff` (Akzent)
- Responsives Layout mit einklappbarer Seitenleiste
- Seitenleisten-Navigation: Dashboard, Aufgaben, Kalender, Zeiterfassung, Kunden, Aufträge, Kanban, Verträge, Rechnungen, Vorgemerkt, Ausgaben, EÜR, Analyse, Dokumente, Einstellungen
- Einheitliche Status-Badges, Tabellen und Formular-Komponenten
- Tab-Zustand in URL-Hash über Seitenaktualisierungen hinweg gespeichert

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

## API-Übersicht

Alle Endpunkte unter `/api/`, geschützt via JWT Bearer Token.

| Methode | Endpunkt | Beschreibung |
|---------|----------|-------------|
| `POST` | `/api/auth/login` | Anmeldung (OAuth2-Formular → JWT) |
| `GET` | `/api/auth/me` | Aktueller Benutzer |
| `GET` | `/api/customers` | Kundenliste (Suche, Paginierung, Sortierung) |
| `GET` | `/api/customers/{id}` | Kundendetail mit Referenzanzahl |
| `POST` | `/api/customers` | Kunde anlegen |
| `PUT` | `/api/customers/{id}` | Kunde aktualisieren |
| `DELETE` | `/api/customers/{id}` | Kunde löschen (mit Referenzprüfung) |
| `GET` | `/api/orders` | Auftragsliste (Filter: Status, Kunde) |
| `POST/PUT/DELETE` | `/api/orders/{id}` | CRUD für Aufträge |
| `GET` | `/api/contracts` | Vertragsliste (Filter: Status, Typ) |
| `POST/PUT/DELETE` | `/api/contracts/{id}` | CRUD für Verträge |
| `GET` | `/api/invoices` | Rechnungsliste (Filter: Status, Kunde) |
| `POST` | `/api/invoices` | Rechnung erstellen (auto. Nummer) |
| `POST` | `/api/invoices/quick` | Schnellrechnung (Einzelposition) |
| `PUT` | `/api/invoices/{id}` | Rechnung aktualisieren |
| `PUT` | `/api/invoices/{id}/status` | Status ändern |
| `POST` | `/api/invoices/{id}/generate-pdf` | PDF generieren |
| `GET` | `/api/invoices/{id}/pdf` | PDF herunterladen |
| `DELETE` | `/api/invoices/{id}` | Löschen (nur Entwürfe) |
| `POST` | `/api/invoices/refresh-drafts` | Alle Rechnungsentwürfe auf heute aktualisieren |
| `GET` | `/api/dashboard/stats` | Dashboard-KPIs |
| `GET` | `/api/tasks` | Aggregierte Aufgabenliste |
| `GET` | `/api/token-tracker/projects` | Projekte aus Token Tracker |
| `GET/POST` | `/api/token-tracker/shares` | Share-Tokens verwalten |
| `DELETE` | `/api/token-tracker/shares/{id}` | Share widerrufen |
| `GET` | `/api/leads` | Lead-Liste (Suche, Status-Filter, Paginierung) |
| `POST` | `/api/leads` | Lead anlegen |
| `PUT` | `/api/leads/{id}` | Lead aktualisieren |
| `DELETE` | `/api/leads/{id}` | Lead löschen |
| `POST` | `/api/invoices/generate-recurring` | Wiederkehrende Rechnungen generieren |
| `POST` | `/api/invoices/{id}/remind` | Zahlungserinnerung senden |
| `POST` | `/api/invoices/{id}/send-email` | Rechnung per E-Mail senden |
| `POST` | `/api/invoices/{id}/send-reminder-email` | Mahnung per E-Mail senden |
| `POST` | `/api/invoices/{id}/generate-reminder-pdf` | Mahnungs-PDF generieren |
| `GET` | `/api/invoices/{id}/reminder-pdf` | Mahnungs-PDF herunterladen |
| `GET/POST/PUT/DELETE` | `/api/time-entries` | Zeiteintrag-CRUD |
| `GET` | `/api/time-entries/summary` | Zeiteintrag-Zusammenfassung |
| `POST` | `/api/orders/{id}/generate-quote-pdf` | Angebots-PDF generieren |
| `GET` | `/api/orders/{id}/quote-pdf` | Angebots-PDF herunterladen |
| `POST` | `/api/orders/{id}/send-quote-email` | Angebot per E-Mail senden |
| `GET` | `/api/activities?customer_id=` | Kontakthistorie |
| `POST` | `/api/activities` | Aktivität erstellen |
| `GET/POST/PUT/DELETE` | `/api/expenses` | Ausgaben-CRUD |
| `GET` | `/api/expenses/summary` | Ausgaben-Zusammenfassung |
| `GET` | `/api/euer/overview` | EÜR-Übersicht |
| `GET` | `/api/euer/export` | EÜR-CSV-Export |
| `GET` | `/api/backup/export` | Vollständiger Datenbank-Export (JSON + PDFs) |
| `POST` | `/api/invoices/{id}/payment` | Teilzahlung erfassen |
| `POST` | `/api/invoices/{id}/credit-note` | Gutschrift erstellen |
| `GET/POST/DELETE` | `/api/attachments` | Dateianhang-CRUD |
| `PATCH` | `/api/attachments/{id}` | Beschreibung/Notizen aktualisieren |
| `GET` | `/api/attachments/{id}/download` | Anhang herunterladen |
| `GET` | `/api/customers/{id}/dsgvo-export` | DSGVO-Datenexport |
| `GET` | `/api/dashboard/charts` | Dashboard-Diagrammdaten |
| `GET` | `/api/dashboard/profitability` | Kunden-Rentabilität |
| `GET` | `/api/dashboard/forecast` | Umsatzprognose |
| `GET` | `/api/dashboard/monthly-report` | Monatsbericht-PDF |
| `GET` | `/api/github/repos` | GitHub-Repositories auflisten |
| `GET/POST/PUT/DELETE` | `/api/email-templates` | E-Mail-Vorlagen-CRUD |
| `POST` | `/api/email-templates/seed` | Standardvorlagen erstellen |
| `GET` | `/api/pagespeed/analyze` | Google PageSpeed PDF-Report (speichert in DB bei customer_id) |
| `GET` | `/api/pagespeed/results` | PageSpeed-Ergebnisse pro Kunde |
| `DELETE` | `/api/pagespeed/results/{id}` | PageSpeed-Ergebnis löschen |
| `GET` | `/api/pagespeed/results/{id}/pdf` | Gespeicherte PageSpeed-PDF herunterladen |
| `GET` | `/api/documents/templates` | Dokumentvorlagen auflisten |
| `POST` | `/api/documents/generate` | Einzelnes Dokument als PDF |
| `POST` | `/api/documents/generate-all` | Alle Dokumente als ZIP |
| `GET` | `/api/documents/preview` | HTML-Vorschau eines Dokuments |
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
cd celox-ops

# Umgebung konfigurieren
cp .env.example .env
# .env bearbeiten: Passwörter, JWT_SECRET, Geschäftsdaten setzen
# Passwort-Hash generieren:
#   python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('dein-passwort'))"
# $ als $$ in .env für Docker Compose escapen

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

Konzipiert für den Betrieb hinter einem Reverse Proxy mit SSL-Terminierung (z.B. Nginx + Let's Encrypt).

- **Port**: 8090 (Docker) — Proxy auf eigene Domain
- **Datenpersistenz**: Docker Volumes für PostgreSQL und PDF-Speicher
- **SSL**: Auf dem Host-Reverse-Proxy konfigurieren

```bash
docker compose up -d --build
```

---

## Besser zusammen: Token Tracker Integration

celox ops und der [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) bilden ein vollständiges Consulting-Toolkit. OPS übernimmt die Geschäftsseite (Kunden, Rechnungen, Verträge), während der Token Tracker die KI-Entwicklungsmetriken erfasst (Sitzungen, Tokens, Kosten, Code-Output).

### Was diese Kombination einzigartig macht

Als IT-Berater, der KI-gestützt entwickelt, stehen Sie vor einer besonderen Herausforderung: Wie dokumentieren Sie transparent, was die KI geleistet hat und was das gekostet hat? celox ops löst genau dieses Problem. Die Kombination aus Geschäftsverwaltung und KI-Nutzungstracking schafft eine lückenlose Kette von der Entwicklungsarbeit bis zur Rechnung — vollautomatisch und nachprüfbar.

### Datenfluss

```
Claude Code → Token Tracker → Share API → celox ops → Kunden-Dashboard + Rechnungs-PDF
```

1. **Claude Code** erzeugt Nutzungsdaten während der KI-gestützten Entwicklung
2. **Token Tracker** sammelt und speichert projektbezogene Metriken (Tokens, Kosten, Codezeilen, aktive Zeit)
3. **Share API** bietet sicheren, token-basierten Zugriff auf Projektmetriken
4. **celox ops** zieht Metriken in die Kundendetailseite und rendert interaktive Dashboards
5. **Rechnungs-PDFs** können einen KI-Nutzungsbericht als Anhangsseite enthalten

### Vorteile für den Berater
- **Transparente Abrechnung** — jede Stunde KI-gestützter Arbeit ist mit nachprüfbaren Metriken dokumentiert
- **Automatisiertes Reporting** — kein manuelles Zeittracking oder Berichtschreiben nötig
- **Kundenvertrauen** — Kunden sehen genau, was getan wurde, wie lange es gedauert hat und was es gekostet hat
- **Ein-Klick-Rechnungsstellung** — professionelles PDF mit KI-Bericht in Sekunden generieren

### Vorteile für den Kunden
- **Nachprüfbare Arbeitsdokumentation** — sitzungsgenaue Details aller KI-gestützten Entwicklung
- **Aktive Zeiterfassung** — echte Arbeitszeit basierend auf Interaktionsmustern, keine aufgeblähten Sitzungsdauern
- **Kostentransparenz** — KI-Kosten pro Sitzung, pro Tag und kumulative Trends einsehbar
- **Exportierbare Berichte** — CSV- und HTML-Exporte für eigene Unterlagen

### Einrichtung

1. **Token Tracker**: Einstellungen → Share API → Admin Key kopieren
2. **celox ops `.env`**: `TOKEN_TRACKER_BASE_URL` und `TOKEN_TRACKER_ADMIN_KEY` setzen
3. **Projekt verknüpfen**: Kunde → Bearbeiten → "Projekt verknüpfen" → Projekt auswählen

### Sicherheit

- Share-Tokens: 192-Bit kryptographisch zufällig (48-Zeichen-Hex)
- Admin Key: 256-Bit, erforderlich für Share-Verwaltung
- Öffentlicher Endpunkt rate-limitiert (30 Req/Min pro IP)
- CORS auf konfigurierte Origins beschränkt
- Keine Projekt-Enumeration möglich
- Optionales Ablaufdatum für Share-Tokens
- Keine internen Pfade oder Bezeichner exponiert

### Aktive Zeiterfassung

Die aktive Arbeitszeit wird aus Nachrichtenzeitstempeln berechnet: Intervalle zwischen aufeinanderfolgenden KI-Interaktionen werden summiert, wobei Lücken > 5 Minuten als inaktiv zählen. Das ergibt realistische Arbeitszeiten (z.B. "5h 15min" statt "194h Sitzungsdauer").

---

## Konfiguration (.env)

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `POSTGRES_USER` | Datenbankbenutzer | `celoxops` |
| `POSTGRES_PASSWORD` | Datenbankpasswort | `sicheres-passwort` |
| `DATABASE_URL` | Asynchroner Connection String | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Token-Signierungsschlüssel | (zufällig, 48+ Zeichen) |
| `ADMIN_USERNAME` | Login-Benutzername | `admin` |
| `ADMIN_PASSWORD_HASH` | bcrypt-Hash des Passworts | `$$2b$$12$$...` |
| `BUSINESS_NAME` | Firmenname (PDFs) | `Ihre Firma` |
| `BUSINESS_OWNER` | Inhabername (PDFs) | `Ihr Name` |
| `BUSINESS_ADDRESS` | Adresse (PDFs) | `Straße, PLZ Ort` |
| `BUSINESS_EMAIL` | E-Mail (PDFs) | `info@beispiel.de` |
| `BUSINESS_TAX_ID` | USt-IdNr. | `DE...` |
| `BUSINESS_BANK_*` | Bankdaten (IBAN, BIC, Name) | für Rechnungs-PDF |
| `BUSINESS_PAYPAL` | PayPal-Adresse (optional) | `du@example.com` |
| `KLEINUNTERNEHMER` | Kleinunternehmerregelung | `true` / `false` |
| `PDF_STORAGE_PATH` | PDF-Speicherpfad | `/data/invoices` |
| `SIGNATURE_PATH` | Pfad zum Unterschrift-Bild (optional) | `/data/assets/signature.png` |
| `TOKEN_TRACKER_BASE_URL` | Token Tracker URL (optional) | `http://host:port` |
| `TOKEN_TRACKER_PUBLIC_URL` | Öffentliche Token Tracker URL (für Browser) | `https://tracker.example.com` |
| `TOKEN_TRACKER_ADMIN_KEY` | Share Admin Key (optional) | (64-Zeichen-Hex) |
| `INVOICE_NUMBER_OFFSET` | Anzahl extern vergebener Rechnungen (optional) | `1` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (optional) | `ghp_...` |
| `GITHUB_USERNAME` | GitHub-Benutzername (optional) | `pepperonas` |
| `PAGESPEED_API_KEY` | Google PageSpeed API-Key (optional) | `AIza...` |
| `SMTP_HOST` | SMTP-Server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP-Port | `587` |
| `SMTP_USER` | SMTP-Benutzername | `user@example.com` |
| `SMTP_PASSWORD` | SMTP-Passwort | (App-Passwort) |
| `SMTP_FROM_EMAIL` | Absender-E-Mail | `info@example.com` |
| `SMTP_FROM_NAME` | Absendername | `Ihre Firma` |

**Sicherheitshinweise:**
- `.env` niemals committen — ist in `.gitignore` eingetragen
- Starke Werte für `JWT_SECRET` und `POSTGRES_PASSWORD` generieren
- `ADMIN_PASSWORD_HASH` muss ein bcrypt-Hash sein (`$` als `$$` escapen)
- `TOKEN_TRACKER_ADMIN_KEY` wird nur bei Nutzung der Token Tracker Integration benötigt
- `GITHUB_TOKEN` gewährt Lesezugriff auf Repositories — verwende einen Token mit minimalen Berechtigungen
- `SIGNATURE_PATH` muss auf eine PNG-Datei im Docker-Volume zeigen (`/data/assets/`)
- Alle persönlichen Daten (Adresse, Steuernummer, Bankverbindung, PayPal) werden ausschließlich in `.env` gespeichert — niemals im Code oder in Templates
- Datenbank-Backups enthalten alle Geschäftsdaten — sicher aufbewahren und nicht weitergeben

---

## Projektstruktur

```
celox-ops/
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
│       │   ├── ...
│       │   ├── lead.py         # Lead-Modell
│       │   ├── time_entry.py   # Zeiteintrag-Modell
│       │   ├── activity.py     # Aktivitätsprotokoll-Modell
│       │   ├── expense.py      # Ausgaben-Modell
│       │   ├── attachment.py   # Dateianhang-Modell
│       │   ├── email_template.py # E-Mail-Vorlagen-Modell
│       │   └── pagespeed_result.py # PageSpeed-Ergebnis-Modell
│       ├── schemas/            # Pydantic v2 Request/Response Schemas
│       │   ├── time_entry.py   # Zeiteintrag-Schemas
│       │   ├── activity.py     # Aktivitätsprotokoll-Schemas
│       │   ├── expense.py      # Ausgaben-Schemas
│       │   ├── email_template.py # E-Mail-Vorlagen-Schemas
│       │   ├── pagespeed_result.py # PageSpeed-Ergebnis-Schemas
│       │   └── ...
│       ├── routers/            # API-Endpunkte (alle paginiert)
│       │   ├── customers.py    # CRUD + Suche + Referenzprüfung
│       │   ├── orders.py       # CRUD + Status/Kunden-Filter
│       │   ├── contracts.py    # CRUD + Status/Typ-Filter
│       │   ├── invoices.py     # CRUD + PDF + Status + Schnellrechnung
│       │   ├── dashboard.py    # Aggregierte KPIs
│       │   ├── leads.py         # Lead-CRUD + Suche + Status-Filter
│       │   ├── tasks.py         # Aggregierte Aufgabenliste
│       │   ├── time_entries.py  # Zeiteintrag-CRUD + Zusammenfassung
│       │   ├── activities.py   # Aktivitätsprotokoll-Endpunkte
│       │   ├── expenses.py     # Ausgaben-CRUD + Zusammenfassung
│       │   ├── euer.py         # EÜR-Übersicht + CSV-Export
│       │   ├── backup.py       # Vollständiger Datenbank-Export (JSON + PDFs)
│       │   ├── token_tracker.py # Token Tracker Share-API-Proxy
│       │   ├── github.py        # GitHub-Integrations-Endpunkte
│       │   ├── attachments.py  # Dateianhang-Endpunkte
│       │   └── email_templates.py # E-Mail-Vorlagen-CRUD
│       ├── services/
│       │   ├── invoice_service.py  # Rechnungsnummer + Berechnung
│       │   ├── pdf_service.py      # WeasyPrint + Jinja2 + KI-Bericht
│       │   ├── email_service.py    # SMTP-E-Mail-Versand
│       │   └── cron_service.py    # Hintergrund-Automatisierung (Überfälligkeitserkennung)
│       └── templates/
│           ├── invoice.html    # A4-Rechnungs-PDF-Template
│           ├── reminder.html   # Mahnungs-PDF-Template
│           ├── quote.html      # Angebots-PDF-Template
│           └── monthly_report.html # Monatsbericht-PDF-Template
│
├── frontend/
│   ├── Dockerfile              # Multi-Stage: Build → Nginx
│   ├── package.json
│   ├── tailwind.config.ts      # Benutzerdefiniertes Dark Theme
│   └── src/
│       ├── App.tsx             # Routing
│       ├── api/                # Axios API-Client + CRUD-Funktionen
│       │   ├── timeEntries.ts  # Zeiteintrag-API
│       │   ├── activities.ts   # Aktivitätsprotokoll-API
│       │   ├── expenses.ts     # Ausgaben-API
│       │   ├── euer.ts         # EÜR-API
│       │   ├── analytics.ts   # Analyse-API
│       │   ├── attachments.ts # Dateianhang-API
│       │   ├── emailTemplates.ts # E-Mail-Vorlagen-API
│       │   ├── github.ts       # GitHub-Integrations-API
│       │   └── ...
│       ├── components/
│       │   ├── Layout.tsx      # Seitenleiste + Header
│       │   ├── DataTable.tsx   # Sortierbar, paginiert
│       │   ├── TokenUsage.tsx  # KI-Nutzungs-Dashboard (Diagramme, KPIs, Export)
│       │   ├── EmailDialog.tsx # Wiederverwendbarer E-Mail-Dialog
│       │   ├── AutocompleteInput.tsx # Intelligente Autovervollständigung für Titel/Beschreibungen
│       │   ├── FileAttachments.tsx # Dateianhang-Komponente
│       │   └── ...             # StatusBadge, FormField, DeleteDialog, Toast
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── Tasks.tsx       # Aggregierte Aufgabenansicht
│       │   ├── Calendar.tsx   # Kalender mit Fristen und Terminen
│       │   ├── TimeTracking.tsx # Zeiterfassungsseite
│       │   ├── Kanban.tsx     # Kanban-Board für Aufträge
│       │   ├── Analytics.tsx  # Kunden-Rentabilität + Umsatzprognose
│       │   ├── Euer.tsx        # EÜR-Übersichtsseite
│       │   ├── customers/      # Liste, Formular, Detail
│       │   ├── orders/         # Liste, Formular, Detail
│       │   ├── contracts/      # Liste, Formular, Detail
│       │   ├── invoices/       # Liste, Formular, Detail
│       │   ├── leads/          # Liste, Formular
│       │   └── expenses/       # Liste, Formular
│       └── utils/
│           ├── formatters.ts   # Datum (DD.MM.YYYY), Währung (1.234,56 EUR)
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
└─────────── Konfigurierbares Präfix
```

---

## Datenbankoptimierung

- PostgreSQL-Indizes auf allen Fremdschlüsseln (customer_id auf orders/contracts/invoices)
- Status-Indizes für gefilterte Abfragen
- Partial Index für offene Rechnungen (Dashboard-Performance)
- Composite Index auf Kundenname+Firma für Suche
- Connection Pooling: pool_size=5, max_overflow=10, pre_ping aktiviert, 5-Min-Recycle
- Token Tracker Aggregator mit 5-Min-TTL gecacht (eliminiert wiederholte Full-Table-Scans)
- GitHub-Repos mit 10-Min-TTL gecacht (eliminiert wiederholte API-Aufrufe)

---

## Lizenz

MIT

---

*Erstellt von [Martin Pfeffer](https://celox.io)*
