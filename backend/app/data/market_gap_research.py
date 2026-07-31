"""Marktradar-Ergänzungsrecherche: Alltagsreibung je Katalogprodukt.

Drei getrennte Ebenen pro Produkt (siehe `GAP_RESEARCH`):

- ``forum_pains``: beobachtete Nutzerreibung aus Bewertungsportalen/Foren/Community
  (Trustpilot, OMR Reviews, Support-Foren, Fachforen) — Formulierung als *erlebte*
  Friktion, nicht als Marketingtext.
- ``vendor_gaps``: was das Herstellerprodukt strukturell NICHT löst bzw. was in
  Excel/E-Mail/Handarbeit hängen bleibt — auch bei korrekter Nutzung des Produkts.
- ``remedies``: wie ein externer Partner/Aufsatz das konkret schließen könnte
  (celox-Angebotslogik: KI-Klassifikation, Aufsatz-/Konnektor-Bau, Audit-Dossiers,
  bcsbook-Muster für Zeiterfassungs-Automatisierung u. Ä. — nie „Prozesse optimieren“).

Reine Datenhaltung, keine Netz-/DB-Zugriffe. Wird vom Marktradar (`services/market_*`)
als Zusatzkontext neben den Katalogfeldern (`pains`, `ki`, `nutzen`, `integration`)
verwendet, um Vertriebsgesprächen konkretere Anker zu geben.

Fünf Einträge (personio, docuware, projektron-bcs, dvelop-documents, otrs) beruhen auf
tatsächlich recherchierten Quellen (Trustpilot/OMR/Support-Foren/ComputerBase/Znuny-
Community, Stand 2026-07). Die übrigen 137 Einträge sind kategorie-realistische,
produktnah formulierte Einschätzungen auf Basis der Produktkategorie und bekannter
Produktmerkmale — keine Zitate, sondern plausible, vertrieblich nutzbare Anker.
"""

from __future__ import annotations

GAP_RESEARCH: dict[str, dict[str, list[str]]] = {
    "dvelop-documents": {
        "forum_pains": [
            "Suche mit vielen Facetten/Filtern wird bei großen Aktenbeständen spürbar langsam",
            "Umstieg von d.3/Explorer auf d.velop documents (cloud) wird als faktisch erzwungener Lizenzwechsel empfunden",
            "Konfiguration von Ablagestrukturen und Rechten braucht Berater, ist für die Fachabteilung allein kaum zu bedienen",
        ],
        "vendor_gaps": [
            "Keine native KI-Klassifikation/Verschlagwortung eingehender Dokumente, Zuordnung bleibt Handarbeit oder Zusatzmodul",
            "Volltextsuche schwächelt bei sehr großen Bibliotheken, kein Feintuning der Relevanz ohne Consulting",
            "Reporting über Ablagequalität/fehlende Verschlagwortung fehlt, Kontrolle läuft über Excel-Exporte",
        ],
        "remedies": [
            "KI-Vorverschlagwortung (Dokumenttyp, Kunde, Kostenstelle) vor der Ablage in d.velop documents",
            "Migrations-/Rechte-Audit vor dem Wechsel von d.3/Explorer auf documents, inkl. Altdaten-Bereinigung",
            "Externes Dashboard über Ablagequalität und offene Freigaben aus den d.velop-Metadaten",
        ],
    },
    "aeb": {
        "forum_pains": [
            "Konfiguration von Zoll-/Exportkontrollregeln für viele Länder erfordert erhebliches Fachwissen und lange Einführungszeit",
            "Updates bei Vorschriftenänderungen (Sanktionslisten, Zolltarife) verlangen sorgfältiges Testen vor der Produktivsetzung",
            "Individuelle Prozessanpassungen binden häufig an den AEB-Partner statt an Eigenpflege im Haus",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung von Exportdokumenten gegen aktuelle Sanktionslisten ohne Zusatzabo",
            "Reporting über Durchlaufzeiten/Ablehnungsquoten im Zollprozess bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Vorprüfung von Export-/Zolldokumenten auf Plausibilität und Sanktionslisten-Treffer vor Einreichung",
            "Ablehnungsquoten-/Durchlaufzeiten-Dashboard aus AEB-Prozessdaten",
        ],
    },
    "personio": {
        "forum_pains": [
            "Nach Vertragsabschluss wird der Support spürbar langsamer, Tickets brauchen Tage statt Stunden",
            "Modul- und Preisstruktur ist intransparent, Zusatzfunktionen werden erst beim Ausbau sichtbar teuer",
            "Cloud-Verfügbarkeit/Performance schwankt, besonders bei Monatswechsel (Lohnabrechnung, Reports) hakt es",
            "Recruiting-Modul: Kandidatensuche und Pipeline-Filter gelten als unhandlich im Vergleich zu dedizierten ATS",
        ],
        "vendor_gaps": [
            "DATEV-Export und eAU-Abwicklung laufen nicht reibungslos automatisch, die Personalabteilung prüft/korrigiert manuell nach",
            "Kein belastbares Reporting über Recruiting-Funnel-Qualität, Auswertung landet in Excel",
            "Vertragsstruktur/Preistransparenz ist beim Verkauf einfacher als im Alltag, spätere Modul-Upgrades sind schwer kalkulierbar",
        ],
        "remedies": [
            "DATEV-/eAU-Übergabe-Check als wiederkehrender automatisierter Abgleich statt manueller Nachkontrolle",
            "KI-gestütztes Kandidaten-Screening/Matching als Aufsatz auf Personio-Recruiting-Daten",
            "Unabhängiges Lizenz-/Modul-Audit vor der nächsten Preisverhandlung mit Personio",
        ],
    },
    "docuware": {
        "forum_pains": [
            "Rechtekonflikte zwischen Workflow- und Archivberechtigungen führen zu Dokumenten, die im Prozess hängen bleiben",
            "\"Neu zuweisen\" bei Freigabe-Workflows reißt die Genehmigungskette ab, niemand fühlt sich mehr zuständig",
            "Stempel-/Sperr-Wettlauf bei parallelem Bearbeiten lässt einzelne Workflow-Schritte ins Leere laufen",
            "Vertretungsregelungen und Eskalationsstufen sind fehleranfällig, bei Krankheit/Urlaub bleiben Vorgänge liegen",
        ],
        "vendor_gaps": [
            "Kein robustes Vertretungs-/Eskalationsmanagement über alle Workflow-Typen hinweg, Workarounds laufen über E-Mail",
            "Fehlende zentrale Übersicht über hängende/blockierte Workflow-Instanzen, Suche danach ist manuell",
            "Cloud-Organisationsstruktur (mehrere File Cabinets/Organisationen) wird bei Wachstum unübersichtlich, kein Self-Service-Reporting",
        ],
        "remedies": [
            "Workflow-Monitor-Aufsatz, der hängende DocuWare-Vorgänge samt Ursache (Rechte/Sperre/fehlende Vertretung) meldet",
            "Automatisierte Vertretungslogik über Kalenderintegration statt manueller Eskalationsregeln",
            "Audit-Dossier aus vorhandenen DMS-Metadaten erzeugen (Nachweis für ISO/DSGVO ohne Zusatzpflege)",
        ],
    },
    "projektron-bcs": {
        "forum_pains": [
            "Einarbeitung gilt als steil, neue Mitarbeitende brauchen Wochen bis zur sicheren Bedienung",
            "Oberfläche wirkt technisch/funktional statt intuitiv, viele Klicks für einfache Buchungen",
            "Mobile Nutzung (Zeiterfassung unterwegs) wird als schwach empfunden, Rückgriff auf Offline-CSV-Import",
            "Admin-Rollen erfordern eigene Schulung, ohne Poweruser stockt die Konfiguration von Projekten/Vorlagen",
        ],
        "vendor_gaps": [
            "Zeiten werden nachträglich erfasst statt automatisch aus Kalender/Ticket/Commit erkannt — Buchungslücken und Rekonstruktion am Monatsende",
            "Keine automatische Projektzuordnung aus Termin oder Tätigkeit, jede Buchung ist manuelle Zuordnungsarbeit",
            "Auswertung über Ist-Zeiten vs. Kalkulation bleibt oft Excel-Nacharbeit statt Live-Sicht im BCS",
        ],
        "remedies": [
            "Aufsatz: Buchungsvorschläge aus Kalender/Tickets/IDE-Aktivität automatisch in BCS schreiben (bcsbook-Muster)",
            "Onboarding-Kurzschulung + Buchungsvorlagen je Rolle, damit neue Mitarbeitende ab Tag 1 korrekt buchen",
            "Mobile Buchungs-Kurzstrecke (Anwesenheit + ein Klick) statt vollständiger BCS-Maske unterwegs",
        ],
    },
    "baramundi": {
        "forum_pains": [
            "Rollout großer Softwarepakete auf viele Endpoints dauert länger als geplant, Fehlerdiagnose bei fehlgeschlagenen Jobs ist mühsam",
            "Rechte-/Rollenkonzept für IT-Teams mit mehreren Standorten wird als unübersichtlich beschrieben",
            "Reporting über Patch-/Compliance-Status wird für Audits manuell zusammengestellt statt auf Knopfdruck",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung kritischer Sicherheitslücken nach Geschäftsrelevanz, Einstufung bleibt Handarbeit der IT",
            "Ticket-/Störungsmeldungen aus dem Feld sind nicht KI-vorklassifiziert, Erstsichtung kostet Zeit",
        ],
        "remedies": [
            "Automatisiertes Schwachstellen-Reporting mit Business-Priorisierung aus baramundi-Inventardaten",
            "Audit-Dossier (Patch-/Compliance-Nachweis) automatisch aus baramundi-Daten für ISO 27001/NIS2",
        ],
    },
    "inloox": {
        "forum_pains": [
            "Bei komplexen Portfolios mit vielen Teilprojekten wird die Oberfläche unübersichtlich, Filter/Ansichten brauchen Einarbeitung",
            "Ressourcenplanung über mehrere Projekte hinweg gilt als weniger ausgereift als bei dedizierten PPM-Tools",
            "Reporting-Vorlagen müssen oft individuell angepasst werden, Standardberichte reichen dem Management selten",
        ],
        "vendor_gaps": [
            "Keine automatische Abgleichung von Ist-Aufwand aus Kalender-/Ticket-Systemen, Zeiterfassung bleibt separate Pflege",
            "Kapazitätsauslastung über Abteilungsgrenzen hinweg wird nicht automatisch aggregiert",
        ],
        "remedies": [
            "Aufsatz, der Kalender-/Ticket-Zeiten automatisch in die InLoox-Zeiterfassung schreibt statt Doppelpflege",
            "Individuelles Management-Reporting (Auslastung, Portfolio-Risiko) aus InLoox-Daten außerhalb der Standardberichte",
        ],
    },
    "aareon-wodis": {
        "forum_pains": [
            "Umstieg von Wodis Sigma auf Yuneo wird als aufwendig beschrieben, Altdaten/Zusatzmodule laufen nicht immer reibungslos mit",
            "Bedienoberfläche gilt für Sachbearbeitende als gewöhnungsbedürftig, viele Wege für Standardvorgänge (Mieterwechsel, Betriebskosten)",
            "Schnittstellen zu Bank-/Zahlungsverkehr und externen Dienstleistern erfordern individuelle Anpassung",
        ],
        "vendor_gaps": [
            "Betriebskostenabrechnung und Mängelmanagement laufen oft parallel in Excel/E-Mail statt vollständig im System",
            "Keine automatische Dokumentenklassifikation für eingehende Post (Rechnungen, Mängelmeldungen, Mieteranfragen)",
        ],
        "remedies": [
            "KI-Eingangspost-Klassifikation (Rechnung/Mängelmeldung/Mieteranfrage) vor Erfassung in Wodis",
            "Migrationsbegleitung Sigma → Yuneo mit Altdaten-Bereinigung statt Big-Bang-Umstieg",
        ],
    },
    "topdesk": {
        "forum_pains": [
            "Konfiguration von Workflows/Kategorien für komplexere Prozesse braucht Admin-Erfahrung, der Standard reicht selten",
            "Self-Service-Portal wird von Endnutzern als wenig intuitiv empfunden, viele landen trotzdem im Telefon-Support",
            "Reporting-Builder gilt als mächtig, aber unhandlich für Gelegenheitsnutzer im Management",
        ],
        "vendor_gaps": [
            "Keine automatische Ticket-Vorklassifikation/Priorisierung ohne Zusatzkonfiguration, Erstsichtung bleibt Teamaufgabe",
            "Wissensdatenbank-Pflege hängt von manueller Redaktion ab, veraltet ohne dediziertes Ownership",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue (Kategorie, Priorität, Dringlichkeit)",
            "Self-Service-Wissensartikel automatisch aus gelösten TOPdesk-Tickets vorschlagen lassen",
        ],
    },
    "hoppe-wartungsplaner": {
        "forum_pains": [
            "Bedienoberfläche wirkt datiert, Einarbeitung für neue Mitarbeitende dauert trotz überschaubarem Funktionsumfang",
            "Mobile Erfassung von Wartungsnachweisen vor Ort ist eingeschränkt, vieles läuft noch über Papier/Excel-Nacherfassung",
        ],
        "vendor_gaps": [
            "Keine automatische Terminierung wiederkehrender Prüfungen aus Herstellervorgaben, Fristen werden manuell nachgehalten",
            "Reporting für Auditoren (Prüfnachweise, Fristenkette) wird per Excel zusammengestellt statt exportiert",
        ],
        "remedies": [
            "Digitale Wartungsnachweis-Erfassung per Smartphone mit automatischem Fristenkalender",
            "Audit-Dossier aus Wartungsplaner-Daten für Betreiberpflichten/Prüfnachweise automatisch erzeugen",
        ],
    },
    "somacos-sessionnet": {
        "forum_pains": [
            "Ratsinformationssystem gilt für ehrenamtliche Gremienmitglieder als wenig selbsterklärend, Schulungsbedarf pro Wahlperiode",
            "Layout/Formatierung von Vorlagen und Tagesordnungspunkten erfordert manuelle Nacharbeit vor Sitzungen",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation/Verschlagwortung eingehender Anträge und Vorlagen",
            "Barrierefreiheit und Volltextsuche über historische Sitzungsunterlagen bleiben ausbaufähig",
        ],
        "remedies": [
            "KI-gestützte Vorlagen-/Antragsklassifikation vor der Tagesordnungserstellung",
            "Volltextsuche-/Barrierefreiheits-Aufsatz über das SessionNet-Archiv",
        ],
    },
    "vertec": {
        "forum_pains": [
            "Individualisierung/Customizing von Auswertungen und Feldern erfordert Vertec-Beratertage, Eigenbau ist begrenzt",
            "Mobile Zeiterfassung wird als funktional, aber wenig komfortabel im Vergleich zu modernen Apps beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Leistungserfassung aus Kalender/E-Mail, jede Stunde muss aktiv gebucht werden",
            "Projektcontrolling-Dashboards sind Basisreports, tiefere BI-Auswertung landet extern",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender-/Mail-Aktivität in Vertec (bcsbook-Muster übertragen)",
            "BI-Dashboard-Aufsatz auf Vertec-Projektdaten für Auslastung/Marge je Mandat",
        ],
    },
    "mpdv-hydra": {
        "forum_pains": [
            "Konfiguration/Customizing für spezifische Fertigungsprozesse erfordert MPDV-Beratung, der Standard passt selten direkt",
            "BDE-Terminals an der Maschine gelten als funktional, aber optisch/bedienseitig in die Jahre gekommen",
        ],
        "vendor_gaps": [
            "Kein automatisches Anomalie-Reporting aus Maschinendaten, Auswertung erfolgt reaktiv nach dem Vorfall",
            "Schnittstellen zu vor-/nachgelagerten Systemen (ERP, QM) brauchen projektspezifische Anpassung",
        ],
        "remedies": [
            "Anomalie-/Ausfall-Frühwarnung als Aufsatz auf HYDRA-Maschinendaten statt reaktiver Auswertung",
            "Schnittstellen-Konnektor HYDRA↔ERP/QM als wiederverwendbare Standardbrücke",
        ],
    },
    "elo-digital": {
        "forum_pains": [
            "Berechtigungskonzept bei gewachsenen Strukturen (viele Mandanten/Abteilungen) wird unübersichtlich",
            "Suche/Verschlagwortung bei großen Aktenbeständen erfordert konsequente Metadatenpflege, sonst versinken Dokumente",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorklassifikation eingehender Dokumente, Verschlagwortung bleibt Aufgabe der Sachbearbeitung",
            "Reporting über Ablagequalität/offene Freigaben fehlt, Kontrolle läuft manuell",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in ELO",
            "Berechtigungs-/Ablage-Audit zur Bereinigung gewachsener ELO-Strukturen",
        ],
    },
    "nevaris": {
        "forum_pains": [
            "Umstieg von Altsystemen auf Nevaris erfordert erheblichen Migrationsaufwand",
            "Kalkulation/AVA-Module gelten als mächtig, aber mit steiler Lernkurve für Neueinsteiger im Bauwesen",
        ],
        "vendor_gaps": [
            "Baustellen-Doku/Aufmaß vor Ort läuft teils noch über Papier/Foto-Mail statt direkt ins System",
            "Rechnungsprüfung/Nachtragsmanagement gegen Aufmaß bleibt manuelle Abgleichsarbeit",
        ],
        "remedies": [
            "Mobile Aufmaß-/Baustellendoku-Erfassung mit direkter Anbindung an Nevaris",
            "KI-gestützter Abgleich Rechnung vs. Aufmaß/Nachtrag vor Freigabe",
        ],
    },
    "atoss": {
        "forum_pains": [
            "Regelwerk für Schichtplanung/Zeitmodelle ist mächtig, aber Konfiguration erfordert Spezialwissen",
            "Self-Service-App für Mitarbeitende wird teils als weniger intuitiv als moderne Consumer-Apps empfunden",
        ],
        "vendor_gaps": [
            "Automatische Schichtvorschläge nach Bedarf/Qualifikation sind Zusatzmodul, die Basis bleibt manuell",
            "Auswertung von Fehlzeitenmustern für Frühwarnung fehlt im Standardreporting",
        ],
        "remedies": [
            "Fehlzeiten-/Auslastungs-Frühwarnung als Dashboard-Aufsatz auf ATOSS-Daten",
            "Vereinfachte Self-Service-Oberfläche für Standardanträge (Urlaub, Tausch) auf Basis der ATOSS-API",
        ],
    },
    "hrworks": {
        "forum_pains": [
            "Bei wachsender Mitarbeiterzahl wird die Konfiguration von Genehmigungsworkflows unübersichtlich",
            "Reporting-Funktionen gelten als Basis, tiefere Personalkennzahlen werden in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine automatische Vertragsfristen-/Probezeit-Überwachung mit proaktiver Eskalation",
            "Onboarding-Checklisten müssen manuell an jede Rolle angepasst werden",
        ],
        "remedies": [
            "Automatisierte Fristen-/Probezeit-Überwachung mit Eskalationsmail statt manueller Kontrolle",
            "HR-Kennzahlen-Dashboard (Fluktuation, Time-to-Hire) aus HRworks-Daten",
        ],
    },
    "easy-software": {
        "forum_pains": [
            "Modulvielfalt (archive/documents/P2P/HR) macht die Lizenz-/Konfigurationsübersicht komplex",
            "Rechnungseingangsworkflow (P2P) erfordert Nachjustierung, sonst bleiben Belege in manueller Prüfung hängen",
        ],
        "vendor_gaps": [
            "OCR-/Belegerkennung erreicht nicht bei allen Lieferantenformaten ausreichende Trefferquote ohne Nachtraining",
            "Reporting über offene Freigaben/Durchlaufzeiten im P2P-Prozess ist rudimentär",
        ],
        "remedies": [
            "KI-Nachtraining der Belegerkennung auf die eigenen Lieferantenformate",
            "Durchlaufzeiten-Dashboard für den EASY-P2P-Freigabeprozess",
        ],
    },
    "connext-vivendi": {
        "forum_pains": [
            "Dokumentationsaufwand in der Pflege wird trotz Software als hoch empfunden, viel Doppelerfassung",
            "Abrechnung mit Kostenträgern erfordert manuelle Nachbearbeitung bei Ablehnungen/Rückfragen",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Leistungsnachweise vor der Abrechnung",
            "Dienstplanung und tatsächliche Anwesenheit werden nicht automatisch abgeglichen",
        ],
        "remedies": [
            "Plausibilitätscheck der Leistungsdokumentation vor Abrechnungslauf, weniger Rückläufer der Kassen",
            "Automatischer Abgleich Dienstplan vs. Anwesenheit als Aufsatz auf Vivendi-Daten",
        ],
    },
    "cas-genesisworld": {
        "forum_pains": [
            "Individualisierung des Datenmodells erfordert CAS-Customizing-Kenntnisse, die Fachabteilung kommt allein nicht weit",
            "Mobile App gilt als funktional, aber weniger modern als Cloud-CRM-Wettbewerber",
        ],
        "vendor_gaps": [
            "Lead-Scoring/Priorisierung ist nicht KI-gestützt, der Vertrieb priorisiert nach Bauchgefühl",
            "Reporting über die Vertriebspipeline erfordert oft externe BI-Anbindung für eine management-taugliche Sicht",
        ],
        "remedies": [
            "KI-Lead-Scoring als Aufsatz auf CAS-genesisWorld-Kontaktdaten",
            "Vertriebs-Dashboard (Pipeline, Forecast) aus CAS-Daten für die Geschäftsführung",
        ],
    },
    "schleupen": {
        "forum_pains": [
            "Releasewechsel/Updates gelten als aufwendig, der Testaufwand für Marktkommunikation (GPKE/MaBiS) ist hoch",
            "Konfiguration der Marktprozesse erfordert Spezialwissen, das intern selten breit vorhanden ist",
        ],
        "vendor_gaps": [
            "Fehleranalyse bei gescheiterten Marktkommunikations-Nachrichten bleibt manuelle Fehlersuche",
            "Reporting für Regulatorik/Bundesnetzagentur-Meldungen wird oft in Excel nachbereitet",
        ],
        "remedies": [
            "Automatisiertes Fehler-Monitoring für Marktkommunikationsnachrichten mit Klartext-Ursache",
            "Regulatorik-Reporting-Aufsatz (Meldepflichten) aus Schleupen-Daten",
        ],
    },
    "adito": {
        "forum_pains": [
            "Der Prozess-Designer ist mächtig, aber die Einarbeitung für Fachabteilungen ohne IT-Hintergrund dauert",
            "Reporting/Dashboards brauchen individuelle Anpassung, der Standard reicht selten für die Vertriebssteuerung",
        ],
        "vendor_gaps": [
            "Keine native KI-Priorisierung von Leads/Opportunities",
            "Datenqualität (Duplikate, veraltete Kontakte) wird nicht automatisch überwacht",
        ],
        "remedies": [
            "Automatische Dublettenbereinigung/Datenqualitäts-Check als ADITO-Aufsatz",
            "KI-Lead-Priorisierung auf Basis vorhandener ADITO-Aktivitätsdaten",
        ],
    },
    "consense": {
        "forum_pains": [
            "Prozesslandkarten-Pflege wird bei häufigen Änderungen als aufwendig empfunden",
            "Freigabeworkflows für Dokumente erfordern Disziplin, sonst laufen alte Versionen weiter im Umlauf",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung veralteter/inkonsistenter Dokumentversionen im Umlauf",
            "Audit-Vorbereitung (Nachweise sammeln) bleibt manuelle Excel-Zusammenstellung",
        ],
        "remedies": [
            "Audit-Dossier automatisch aus ConSense-Dokumenten- und Freigabedaten erzeugen",
            "Automatische Alt-Versions-/Inkonsistenz-Erkennung im QM-Dokumentenbestand",
        ],
    },
    "zep": {
        "forum_pains": [
            "Zeiterfassung erfolgt oft nachträglich am Wochenende/Monatsende statt tagesaktuell",
            "Projektstrukturen/Kostenstellen-Konfiguration erfordert Admin-Einarbeitung bei komplexeren Kundenprojekten",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender, Tickets oder Entwicklungswerkzeugen — jede Stunde ist Handeingabe",
            "Reporting über Ist vs. Budget je Projekt bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in ZEP (bcsbook-Muster)",
            "Ist-/Budget-Frühwarnung je Projekt als Dashboard-Aufsatz auf ZEP-Daten",
        ],
    },
    "enventa-nissen-velten": {
        "forum_pains": [
            "Customizing für branchenspezifische Prozesse erfordert Partnerunterstützung, der Standard reicht selten",
            "Reporting-Werkzeuge gelten als technisch, für Fachbereiche ohne BI-Erfahrung schwer zugänglich",
        ],
        "vendor_gaps": [
            "Keine automatische Bedarfsprognose/Nachbestellvorschläge ohne Zusatzmodul",
            "Belegerkennung im Rechnungseingang ist nicht Teil des Kernsystems, läuft über Fremdtool oder manuell",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in eNVenta",
            "BI-Reporting-Aufsatz für Fachbereiche ohne eigene BI-Kompetenz",
        ],
    },
    "onventis": {
        "forum_pains": [
            "Lieferantenanbindung (Katalog/Punch-out) erfordert individuelle Einrichtung je Lieferant",
            "Freigabeworkflows bei komplexen Bestellstrukturen werden als unübersichtlich beschrieben",
        ],
        "vendor_gaps": [
            "Bedarfsbündelung über Abteilungen hinweg wird nicht automatisch vorgeschlagen",
            "Rechnungsabgleich (3-Way-Match) erfordert bei Abweichungen manuelle Klärung außerhalb des Systems",
        ],
        "remedies": [
            "Automatisierter 3-Way-Match mit KI-gestützter Abweichungsklärung",
            "Bedarfsbündelungs-Dashboard über Abteilungen aus Onventis-Bestelldaten",
        ],
    },
    "greengate-gs-service": {
        "forum_pains": [
            "Mobile Erfassung von Störmeldungen/Wartungsaufträgen vor Ort wird als ausbaufähig beschrieben",
            "Konfiguration von Wartungsplänen für heterogene Anlagenparks erfordert viel Detailpflege",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Störmeldungen nach Kritikalität",
            "Prüffristen-Reporting für Auditoren wird manuell zusammengestellt",
        ],
        "remedies": [
            "KI-Priorisierung eingehender Störmeldungen nach Kritikalität/SLA",
            "Automatisiertes Prüffristen-Dossier aus GS-Service-Daten",
        ],
    },
    "qwiki-modell-aachen": {
        "forum_pains": [
            "Die wiki-artige Struktur erfordert konsequente Redaktion, sonst veralten Prozessbeschreibungen unbemerkt",
            "Suche über viele verlinkte Seiten wird bei großen Organisationen unübersichtlich",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung verwaister oder veralteter Prozessseiten",
            "Audit-Nachweise müssen manuell aus einzelnen Wiki-Seiten zusammengetragen werden",
        ],
        "remedies": [
            "Automatische Alt-/Verwaisungs-Erkennung im Q.wiki-Prozessbestand",
            "Audit-Dossier-Generator aus Q.wiki-Freigabehistorie",
        ],
    },
    "abas-erp": {
        "forum_pains": [
            "Individuelle Anpassungen (ABAS-eigene Skriptsprache) binden an den Partner, Eigenpflege ist begrenzt",
            "Reporting/BI-Auswertung wird häufig extern (Excel/BI-Tool) nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-gestützte Bedarfs-/Absatzprognose",
            "Rechnungseingangsverarbeitung ohne Zusatzmodul bleibt weitgehend manuell",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in abas ERP",
            "BI-Dashboard-Aufsatz für Vertrieb/Fertigung aus abas-Daten",
        ],
    },
    "papershift": {
        "forum_pains": [
            "Bei komplexeren Schichtmodellen (mehrere Standorte, Qualifikationen) wird die Planung als eingeschränkt beschrieben",
            "Zeiterfassung per App wird gelegentlich als fehleranfällig bei Verbindungsproblemen genannt",
        ],
        "vendor_gaps": [
            "Keine automatische Schichtvorschlags-KI nach Bedarf/Verfügbarkeit",
            "Auswertung von Überstunden-/Fehlzeitenmustern bleibt Basis-Reporting",
        ],
        "remedies": [
            "KI-gestützte Schichtvorschläge auf Basis von Bedarf, Verfügbarkeit und Qualifikation",
            "Überstunden-/Fehlzeiten-Frühwarnung als Dashboard-Aufsatz auf Papershift-Daten",
        ],
    },
    "proalpha": {
        "forum_pains": [
            "Customizing-Aufwand bei Prozessänderungen wird als hoch beschrieben, die Partnerabhängigkeit ist spürbar",
            "Das Reporting-Cockpit gilt als solide, aber für Ad-hoc-Analysen wird meist Excel genutzt",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Bestell-/Lagerdaten",
            "Rechnungseingang ohne Zusatzmodul bleibt weitgehend manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung und Abweichungsprüfung vor Verbuchung in proALPHA",
            "Anomalie-Dashboard für Bestand/Bestellungen aus proALPHA-Daten",
        ],
    },
    "pds": {
        "forum_pains": [
            "Mobile Auftragsbearbeitung für Monteure im Feld gilt als funktional, aber nicht immer intuitiv",
            "Stammdatenpflege (Material, Preise) erfordert regelmäßigen manuellen Aufwand",
        ],
        "vendor_gaps": [
            "Keine automatische Angebots-/Rechnungsprüfung gegen erfasste Aufmaße",
            "Reporting über Auftragsrentabilität je Kunde/Gewerk bleibt Excel-Auswertung",
        ],
        "remedies": [
            "KI-Abgleich Aufmaß vs. Rechnung vor Freigabe",
            "Rentabilitäts-Dashboard je Auftrag/Kunde aus pds-Daten",
        ],
    },
    "otrs": {
        "forum_pains": [
            "Die Oberfläche gilt als in die Jahre gekommen, viele Teams wechseln aus Usability-Gründen zu Zammad oder anderen Tools",
            "LDAP-/Nutzerverwaltung über Konfigurationsdateien statt GUI wird als admin-lastig beschrieben",
            "Viele Forks (Znuny, KIX) verwirren bei der Versions-/Supportwahl",
        ],
        "vendor_gaps": [
            "Ticket-Klassifikation ohne Zusatzmodul ist rein regelbasiert, keine echte inhaltliche Priorisierung",
            "Reporting-Dashboards für management-taugliche KPIs erfordern zusätzliche Konfiguration/Statistikmodule",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue (Kategorie, Priorität, Dringlichkeit)",
            "Migrationsberatung OTRS → Znuny/KIX/Zammad inkl. Altdaten- und Rechteübernahme",
            "Management-Dashboard (SLA, Durchlaufzeit) aus OTRS-Statistikdaten",
        ],
    },
    "orgavision": {
        "forum_pains": [
            "Prozessdiagramme/Freigabeworkflows erfordern konsequente Pflege, sonst driftet die Doku von der Praxis ab",
            "Die Suche über größere Wissensbestände wird als verbesserungswürdig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung von Prozess-Doku, die nicht mehr zur gelebten Praxis passt",
            "Audit-Vorbereitung bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus orgavision-Freigabehistorie",
            "KI-Abgleich Prozessdoku vs. tatsächlich gelebte Abläufe (aus Ticket-/Vorgangsdaten)",
        ],
    },
    "omnitracker": {
        "forum_pains": [
            "Der Formular-/Workflow-Designer ist mächtig, aber die Konfiguration erfordert erfahrene Admins",
            "Bei vielen Anwendungsfällen (ITSM, GRC, individuelle Apps) wird die Plattform als komplex in der Governance beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Ticketklassifikation, die Vorklassifikation bleibt regelbasiert",
            "Reporting über mehrere OMNITRACKER-Anwendungen hinweg erfordert zusätzliche BI-Anbindung",
        ],
        "remedies": [
            "KI-Vorklassifikation eingehender Vorgänge vor Verteilung in OMNITRACKER",
            "Übergreifendes Reporting-Dashboard aus mehreren OMNITRACKER-Anwendungen",
        ],
    },
    "cosinex": {
        "forum_pains": [
            "Die Bedienoberfläche für Bieter gilt teils als wenig intuitiv, Rückfragen zum Hochladen von Unterlagen häufen sich",
            "Konfiguration komplexer Vergabeverfahren erfordert Einarbeitung der Vergabestelle",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung eingereichter Angebotsunterlagen vor der formalen Prüfung",
            "Auswertung/Statistik über die Verfahrensdauer je Vergabeart bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Vorprüfung eingereichter Vergabeunterlagen auf Vollständigkeit/Formfehler",
            "Verfahrensdauer-Dashboard aus cosinex-Daten für Vergabestellen",
        ],
    },
    "immoware24": {
        "forum_pains": [
            "Bei Sonderfällen (gemischte Portfolios WEG/Miete) wird die Konfiguration als unübersichtlich beschrieben",
            "Mieter-/Eigentümerkommunikation läuft teils noch parallel per E-Mail statt vollständig im Portal",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation eingehender Post (Rechnung, Mängelmeldung, Kündigung)",
            "Betriebskostenabrechnung erfordert manuelle Prüfung bei Abweichungen",
        ],
        "remedies": [
            "KI-Eingangspost-Klassifikation vor Erfassung in Immoware24",
            "Automatisierte Plausibilitätsprüfung der Betriebskostenabrechnung vor Versand",
        ],
    },
    "babtec": {
        "forum_pains": [
            "Reklamationsmanagement-Konfiguration für komplexe Lieferketten erfordert Spezialwissen",
            "Reporting/Statistik-Auswertung wird für Managementpräsentationen oft in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine automatische Ursachen-Clusterung bei gehäuften Reklamationen",
            "Audit-Vorbereitung (IATF/ISO 9001) bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "KI-Clusterung von Reklamationsursachen aus BabtecQ-Daten für schnellere Root-Cause-Analyse",
            "Audit-Dossier-Generator aus BabtecQ-Nachweisen für IATF/ISO 9001",
        ],
    },
    "soloplan-carlo": {
        "forum_pains": [
            "Disposition bei kurzfristigen Änderungen (Ausfälle, Stau) erfordert viel manuelle Nachplanung",
            "Schnittstellen zu Kunden-/Frachtführerportalen brauchen individuelle Anpassung je Partner",
        ],
        "vendor_gaps": [
            "Keine automatische Frachtführerauswahl nach Preis/Verfügbarkeit/Historie",
            "Track-and-Trace-Kommunikation an Kunden läuft teils manuell per Telefon/E-Mail",
        ],
        "remedies": [
            "Automatisierte Frachtführer-Empfehlung aus CarLo-Historiendaten",
            "Automatisches Track-and-Trace-Kundenupdate aus CarLo-Statusdaten",
        ],
    },
    "casavi": {
        "forum_pains": [
            "Die Ticketflut aus Mieteranfragen wird bei größeren Portfolios als schwer priorisierbar beschrieben",
            "Integration mit Bestandsverwaltungssoftware erfordert bei manchen Kombinationen manuelle Nacharbeit",
        ],
        "vendor_gaps": [
            "Keine automatische Vorklassifikation/Priorisierung eingehender Mieteranfragen",
            "Reporting über Reaktionszeiten/Zufriedenheit bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Vorklassifikation eingehender casavi-Anfragen nach Dringlichkeit/Thema",
            "SLA-/Reaktionszeit-Dashboard aus casavi-Daten für die Hausverwaltung",
        ],
    },
    "enaio-optimal-systems": {
        "forum_pains": [
            "Bei großen Aktenbeständen wird die Suche/Performance als ausbaufähig beschrieben",
            "Konfiguration von Workflows für spezifische Fachprozesse erfordert Partner-Know-how",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Reporting über Ablagequalität/Fristen bleibt manuelle Auswertung",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in enaio",
            "Fristen-/Ablagequalitäts-Dashboard aus enaio-Metadaten",
        ],
    },
    "ams-erp": {
        "forum_pains": [
            "Customizing für Sonderprozesse in Einzel-/Auftragsfertigung erfordert Beraterunterstützung",
            "Reporting wird häufig extern in Excel/BI nachgezogen",
        ],
        "vendor_gaps": [
            "Keine automatische Kapazitäts-/Terminfrühwarnung bei Auftragsverzug",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in ams.erp",
            "Terminverzug-Frühwarnung als Dashboard-Aufsatz auf ams.erp-Auftragsdaten",
        ],
    },
    "otris": {
        "forum_pains": [
            "Konfiguration von Vertragsfristen/Eskalationsketten für viele Vertragstypen erfordert Detailpflege",
            "Suche über umfangreiche Vertrags-/Compliance-Bestände wird bei Wachstum langsamer",
        ],
        "vendor_gaps": [
            "Keine automatische Risikobewertung neuer Verträge vor der Freigabe",
            "Audit-Vorbereitung (Compliance-Nachweise) bleibt manuelle Zusammenstellung",
        ],
        "remedies": [
            "KI-Risikocheck neuer Verträge vor Freigabe in otris contract",
            "Audit-Dossier-Generator aus otris-Compliance-Daten",
        ],
    },
    "loy-hutz-waveware": {
        "forum_pains": [
            "Mobile Instandhaltungserfassung vor Ort wird als ausbaufähig beschrieben, viel Nacherfassung am PC",
            "Konfiguration von Wartungsplänen für heterogene Anlagen erfordert erheblichen Ersteinrichtungsaufwand",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Störmeldungen nach Kritikalität/SLA",
            "Prüffristen-Reporting für Auditoren bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Priorisierung eingehender Störmeldungen nach Kritikalität",
            "Automatisiertes Prüffristen-Dossier aus waveware-Daten",
        ],
    },
    "proxia": {
        "forum_pains": [
            "Konfiguration für heterogene Maschinenparks (viele Protokolle) erfordert erheblichen Integrationsaufwand",
            "BDE-Terminals an der Maschine gelten als funktional, aber wenig zeitgemäß in der Bedienung",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Maschinen-/Prozessdaten",
            "Reporting für OEE/Stillstandsursachen bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Anomalie-/Stillstands-Frühwarnung als Aufsatz auf PROXIA-MES-Daten",
            "OEE-Reporting-Dashboard aus PROXIA-Daten ohne Excel-Umweg",
        ],
    },
    "peakavenue-iqs": {
        "forum_pains": [
            "Die Zusammenführung der beiden Produktlinien (iqs, PLATO e1ns) sorgt für Unsicherheit bei Bestandskunden zur Roadmap",
            "Konfiguration von FMEA-/Reklamationsprozessen erfordert erfahrene QM-Admins",
        ],
        "vendor_gaps": [
            "Keine automatische Ursachen-Clusterung bei gehäuften Reklamationen",
            "Audit-Vorbereitung bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "KI-Clusterung von Reklamationsursachen aus iqs-Daten",
            "Audit-Dossier-Generator aus iqs/PLATO-Freigabehistorie",
        ],
    },
    "diamant-software": {
        "forum_pains": [
            "Das Reporting-Cockpit gilt als solide, aber für Ad-hoc-Auswertungen wird häufig Excel genutzt",
            "Schnittstellen zu Vorsystemen (Zeiterfassung, Warenwirtschaft) erfordern individuelle Anpassung",
        ],
        "vendor_gaps": [
            "Keine automatische Belegerkennung/Kontierungsvorschläge ohne Zusatzmodul",
            "Liquiditätsplanung bleibt teils Excel-Nacharbeit außerhalb von Diamant",
        ],
        "remedies": [
            "KI-Belegerkennung mit Kontierungsvorschlägen vor Verbuchung in Diamant/4",
            "Liquiditäts-Dashboard aus Diamant-Daten ohne Excel-Umweg",
        ],
    },
    "blue-ant-proventis": {
        "forum_pains": [
            "Konfiguration von Projektvorlagen/Ressourcenplanung erfordert Einarbeitung, der Standard passt selten direkt",
            "Zeiterfassung wird teils als nachträgliche Pflicht statt tagesaktueller Routine beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender/Tickets — jede Stunde ist Handeingabe",
            "Auswertung Ist vs. Budget je Projekt bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in Blue Ant (bcsbook-Muster)",
            "Ist-/Budget-Frühwarnung je Projekt als Dashboard-Aufsatz",
        ],
    },
    "riege-scope": {
        "forum_pains": [
            "Konfiguration für komplexe Zoll-/Frachtprozesse erfordert Speditionsfachwissen und Einarbeitungszeit",
            "Schnittstellen zu Reedereien/Airlines/Zoll erfordern laufende Pflege bei Formatänderungen",
        ],
        "vendor_gaps": [
            "Keine automatische Dokumentenklassifikation eingehender Frachtpapiere",
            "Abweichungen zwischen Buchung und tatsächlicher Sendung werden nicht automatisch geflaggt",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Frachtdokumente vor Erfassung in Scope",
            "Automatischer Abgleich Buchung vs. Sendungsdaten mit Abweichungswarnung",
        ],
    },
    "fastec": {
        "forum_pains": [
            "BDE-Erfassung an der Maschine wird als funktional, aber bedienseitig verbesserungswürdig beschrieben",
            "Konfiguration für neue Fertigungslinien erfordert Partnerunterstützung",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung/Stillstandsanalyse ohne Zusatzauswertung",
            "OEE-Reporting bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Stillstands-/Anomalie-Frühwarnung als Aufsatz auf FASTEC-4-PRO-Daten",
            "OEE-Dashboard aus FASTEC-Daten ohne Excel-Umweg",
        ],
    },
    "xentral": {
        "forum_pains": [
            "Bei individuellen Prozessen stößt die Konfigurierbarkeit an Grenzen, Workarounds über externe Tools/Zapier sind üblich",
            "Die Support-Reaktionszeit wird bei komplexeren Fällen als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose für Nachbestellungen",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in Xentral",
            "Bedarfsprognose-/Nachbestell-Dashboard aus Xentral-Verkaufsdaten",
        ],
    },
    "cobra-crm": {
        "forum_pains": [
            "Individualisierung des Datenmodells erfordert Customizing-Kenntnisse",
            "Mobile Nutzung gilt als funktional, aber wenig modern im Vergleich zu Cloud-CRM",
        ],
        "vendor_gaps": [
            "Keine native KI-Lead-Priorisierung",
            "Reporting für management-taugliche Vertriebs-KPIs erfordert externe Auswertung",
        ],
        "remedies": [
            "KI-Lead-Scoring als Aufsatz auf cobra-Kontaktdaten",
            "Vertriebs-Dashboard (Pipeline, Forecast) aus cobra-Daten",
        ],
    },
    "xsuite": {
        "forum_pains": [
            "Konfiguration von Freigabeworkflows für komplexe Kostenstellenstrukturen erfordert SAP-Know-how",
            "Ausnahmefälle (unklare Zuordnung, Sonderformate) landen trotzdem in manueller Klärung",
        ],
        "vendor_gaps": [
            "Belegerkennung erreicht nicht bei allen Lieferantenformaten ausreichende Trefferquote ohne Nachtraining",
            "Reporting über Durchlaufzeiten im Freigabeprozess bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Nachtraining der Belegerkennung auf eigene Lieferantenformate",
            "Durchlaufzeiten-Dashboard für den xSuite-Freigabeprozess",
        ],
    },
    "gfos": {
        "forum_pains": [
            "Konfiguration komplexer Schichtmodelle und Zutrittsregeln erfordert Spezialwissen",
            "Die Self-Service-Oberfläche für Mitarbeitende gilt als funktional, aber nicht immer intuitiv",
        ],
        "vendor_gaps": [
            "Keine automatische Schichtvorschlags-KI nach Bedarf/Qualifikation",
            "Auswertung von Zutritts-/Anwesenheitsmustern für Sicherheits-Reporting bleibt Basis",
        ],
        "remedies": [
            "KI-gestützte Schichtvorschläge auf Basis von Bedarf und Qualifikation",
            "Sicherheits-/Anwesenheits-Dashboard aus GFOS-Zutrittsdaten",
        ],
    },
    "i-doit": {
        "forum_pains": [
            "Die Pflege der CMDB bei großen, sich ändernden Infrastrukturen erfordert Disziplin, sonst veraltet der Bestand schnell",
            "Individuelle Objekttypen/Reports erfordern Konfigurationsaufwand",
        ],
        "vendor_gaps": [
            "Keine automatische Discovery-Abgleichung/Anomalieerkennung im Standard ohne Zusatzmodul",
            "Reporting für Audits (ISO 27001, NIS2) bleibt manuelle Zusammenstellung",
        ],
        "remedies": [
            "Automatisierter CMDB-Abgleich mit tatsächlicher Infrastruktur (Discovery-Aufsatz)",
            "Audit-Dossier-Generator aus i-doit-Daten für ISO 27001/NIS2",
        ],
    },
    "cronetwork-industrie-informatik": {
        "forum_pains": [
            "Konfiguration für heterogene Fertigungslinien erfordert erheblichen Integrationsaufwand",
            "BDE-Bedienung an der Maschine gilt als funktional, aber wenig intuitiv für neue Mitarbeitende",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Maschinendaten",
            "OEE-/Stillstandsreporting bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Anomalie-/Stillstands-Frühwarnung als Aufsatz auf cronetwork-Daten",
            "OEE-Dashboard aus cronetwork-Daten ohne Excel-Umweg",
        ],
    },
    "roxtra": {
        "forum_pains": [
            "Dokumentenlenkung/Freigabeworkflows erfordern konsequente Pflege, sonst laufen alte Versionen weiter um",
            "Suche über größere QM-Dokumentenbestände wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung veralteter/inkonsistenter Dokumentversionen",
            "Audit-Vorbereitung bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus roXtra-Freigabehistorie",
            "Automatische Alt-Versions-Erkennung im QM-Dokumentenbestand",
        ],
    },
    "myneva": {
        "forum_pains": [
            "Der Dokumentationsaufwand in der Behinderten-/Sozialhilfe wird trotz Software als hoch empfunden",
            "Abrechnung mit Kostenträgern erfordert manuelle Nachbearbeitung bei Rückfragen",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Leistungsdokumentation vor der Abrechnung",
            "Dienstplanung und Ist-Anwesenheit werden nicht automatisch abgeglichen",
        ],
        "remedies": [
            "Plausibilitätscheck der Leistungsdokumentation vor Abrechnungslauf",
            "Automatischer Abgleich Dienstplan vs. Anwesenheit als Aufsatz auf myneva-Daten",
        ],
    },
    "aconso": {
        "forum_pains": [
            "Die Migration bestehender Papier-/Altakten in die digitale Personalakte wird als aufwendig beschrieben",
            "Freigabeworkflows für Dokumente erfordern klare Rollenpflege, sonst kommt es zu Verzögerungen",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation eingehender HR-Dokumente vor der Ablage",
            "Fristenüberwachung (Verträge, Zeugnisse) läuft teils parallel in Excel",
        ],
        "remedies": [
            "KI-Klassifikation eingehender HR-Dokumente vor Ablage in aconso",
            "Automatisierte Fristenüberwachung (Verträge, Befristungen) mit Eskalation",
        ],
    },
    "mobilex": {
        "forum_pains": [
            "Disposition bei kurzfristigen Änderungen erfordert viel manuelle Nachplanung",
            "Die mobile App für Techniker gilt als funktional, aber die Offline-Fähigkeit wird als verbesserungswürdig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Technikerauswahl nach Qualifikation/Verfügbarkeit/Standort",
            "Reporting über Reaktionszeiten/SLA bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-gestützte Techniker-Disposition nach Qualifikation, Standort und SLA",
            "SLA-/Reaktionszeit-Dashboard aus mobileX-Daten",
        ],
    },
    "ix-haus-crem": {
        "forum_pains": [
            "Bei komplexen Portfolios (WEG + Miete + Gewerbe) wird die Konfiguration als anspruchsvoll beschrieben",
            "Betriebskostenabrechnung erfordert manuelle Prüfung bei Abweichungen",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation eingehender Post (Rechnung, Mängelmeldung)",
            "Mängelmanagement läuft teils parallel per E-Mail statt vollständig im System",
        ],
        "remedies": [
            "KI-Eingangspost-Klassifikation vor Erfassung in iX-Haus",
            "Automatisierte Plausibilitätsprüfung der Betriebskostenabrechnung",
        ],
    },
    "jedox": {
        "forum_pains": [
            "Die Modellierung komplexer Planungsmodelle erfordert Excel-/OLAP-Erfahrung, die Einarbeitung dauert",
            "Die Performance bei sehr großen Würfeln/Datenmengen wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Planzahlen/Abweichungsanalysen",
            "Datenanbindung an Vorsysteme erfordert individuelle ETL-Pflege",
        ],
        "remedies": [
            "Automatisierte Abweichungs-/Anomalie-Erkennung in Jedox-Planzahlen",
            "ETL-Konnektor Jedox↔Vorsysteme als wiederverwendbare Standardbrücke",
        ],
    },
    "doxis-ser": {
        "forum_pains": [
            "Konfiguration von Content-Automatisierungs-Workflows erfordert Partner-Know-how",
            "Suche über große Aktenbestände wird bei Wachstum spürbar langsamer",
        ],
        "vendor_gaps": [
            "Keine automatische Nachprüfung der KI-Klassifikationsqualität im laufenden Betrieb",
            "Reporting über Ablagequalität/offene Freigaben bleibt manuelle Auswertung",
        ],
        "remedies": [
            "Qualitätsmonitoring der Doxis-KI-Klassifikation mit Nachtraining",
            "Ablagequalitäts-Dashboard aus Doxis-Metadaten",
        ],
    },
    "unite-mercateo": {
        "forum_pains": [
            "Lieferantenkatalog-Pflege und Sonderbestellungen außerhalb des Katalogs erfordern manuelle Nacharbeit",
            "Freigabeworkflows bei komplexen Bestellstrukturen werden als unübersichtlich beschrieben",
        ],
        "vendor_gaps": [
            "Bedarfsbündelung über Abteilungen hinweg wird nicht automatisch vorgeschlagen",
            "Rechnungsabgleich bei Abweichungen erfordert manuelle Klärung",
        ],
        "remedies": [
            "Automatisierter Rechnungsabgleich mit KI-gestützter Abweichungsklärung",
            "Bedarfsbündelungs-Dashboard aus Unite-Bestelldaten",
        ],
    },
    "setlog-osca": {
        "forum_pains": [
            "Die Anbindung vieler Lieferanten mit unterschiedlicher Datenqualität erfordert laufende manuelle Pflege",
            "Eskalationen bei Lieferverzug werden teils noch parallel per E-Mail koordiniert",
        ],
        "vendor_gaps": [
            "Keine automatische Risikoprognose für Lieferverzögerungen aus Historiendaten",
            "Reporting über Lieferantenperformance bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Risikoprognose für Lieferverzug aus OSCA-Historiendaten",
            "Lieferantenperformance-Dashboard aus OSCA-Daten ohne Excel-Umweg",
        ],
    },
    "weclapp": {
        "forum_pains": [
            "Bei individuellen Prozessen stößt die Konfigurierbarkeit an Grenzen, Workarounds über Zusatztools sind üblich",
            "Die Support-Reaktionszeit wird bei komplexeren Fällen als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in weclapp",
            "Bedarfsprognose-Dashboard aus weclapp-Verkaufsdaten",
        ],
    },
    "kix": {
        "forum_pains": [
            "Die Migration von OTRS zu KIX erfordert sorgfältige Planung, Altdaten/Workflows übernehmen sich nicht immer 1:1",
            "Konfiguration von Automatisierungsregeln erfordert Admin-Erfahrung",
        ],
        "vendor_gaps": [
            "Keine native KI-Ticketklassifikation, die Priorisierung bleibt regelbasiert",
            "Reporting-Dashboards für Management-KPIs erfordern zusätzliche Konfiguration",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue",
            "Migrationsbegleitung OTRS → KIX inkl. Altdaten- und Rechteübernahme",
        ],
    },
    "magicline": {
        "forum_pains": [
            "Die Mitgliederverwaltung bei mehreren Standorten wird als konfigurationsaufwendig beschrieben",
            "Kündigungsprozesse/Widerrufe erfordern teils manuelle Nachbearbeitung",
        ],
        "vendor_gaps": [
            "Keine automatische Absage-/Churn-Frühwarnung aus Nutzungsdaten",
            "Reporting über Standortvergleiche bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Churn-Frühwarnung (Kündigungsrisiko) als Dashboard-Aufsatz auf Magicline-Nutzungsdaten",
            "Standortvergleichs-Dashboard aus Magicline-Daten ohne Excel-Umweg",
        ],
    },
    "lucanet": {
        "forum_pains": [
            "Die Konfiguration von Konsolidierungskreisen bei komplexen Konzernstrukturen erfordert Fachwissen",
            "Datenanbindung an Vorsysteme erfordert individuelle Schnittstellenpflege",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Konsolidierungsdaten",
            "Reporting für Ad-hoc-Analysen wird teils extern in Excel nachgezogen",
        ],
        "remedies": [
            "ETL-Konnektor LucaNet↔Vorsysteme als wiederverwendbare Standardbrücke",
            "Anomalie-/Abweichungs-Dashboard auf LucaNet-Konsolidierungsdaten",
        ],
    },
    "nexus-ag": {
        "forum_pains": [
            "Bei Systemwechsel/Modulerweiterung wird der Migrationsaufwand als hoch beschrieben",
            "Die Bedienoberfläche für die Dokumentation gilt bei Klinikpersonal als zeitintensiv",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Abrechnungsdokumentation vor der Übermittlung",
            "Reporting für Qualitätsmanagement/Audits bleibt manuelle Zusammenstellung",
        ],
        "remedies": [
            "Plausibilitätscheck der Abrechnungsdokumentation vor der Übermittlung",
            "Audit-/QM-Dossier-Generator aus NEXUS-Dokumentationsdaten",
        ],
    },
    "hiscout": {
        "forum_pains": [
            "Konfiguration der Module (ISM, Grundschutz, Datenschutz, BCM) erfordert Fachwissen und Zeit",
            "Reporting für Managementpräsentationen wird teils extern nachbereitet",
        ],
        "vendor_gaps": [
            "Keine automatische Risikobewertung neuer Assets/Prozesse",
            "Audit-Vorbereitung bleibt teils manuelle Nachweissammlung trotz GRC-Tool",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus HiScout-Daten für ISO 27001/NIS2/DSGVO",
            "KI-gestützte Risikobewertung neuer Assets/Prozesse in HiScout",
        ],
    },
    "softgarden": {
        "forum_pains": [
            "Kandidatensuche/-filterung in großen Bewerberpools gilt als weniger komfortabel als bei spezialisierten ATS",
            "Individualisierung von Karriereseiten/Formularen erfordert technisches Know-how",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorqualifikation von Bewerbungen",
            "Reporting über Recruiting-Funnel-Qualität bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-gestützte Bewerbervorqualifikation/Matching als softgarden-Aufsatz",
            "Recruiting-Funnel-Dashboard aus softgarden-Daten",
        ],
    },
    "applus-asseco": {
        "forum_pains": [
            "Customizing für Sonderprozesse erfordert Partnerunterstützung, der Standard reicht selten",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in APplus",
            "Bedarfsprognose-Dashboard aus APplus-Verkaufsdaten",
        ],
    },
    "consol-cm": {
        "forum_pains": [
            "Die Konfiguration des Prozess-Designers erfordert erfahrene Admins, die Standardauslieferung reicht selten",
            "Individualisierung von Masken/Workflows dauert bei komplexen Fällen länger als geplant",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorklassifikation eingehender Vorgänge",
            "Reporting über Bearbeitungszeiten/SLA bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Vorklassifikation eingehender Vorgänge vor Verteilung in ConSol CM",
            "SLA-/Bearbeitungszeit-Dashboard aus ConSol-CM-Daten",
        ],
    },
    "steps-step-ahead": {
        "forum_pains": [
            "Customizing/Individualisierung erfordert Partner-Know-how",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose oder Anomalieerkennung",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in STEPS Business Solution",
            "Anomalie-Dashboard für Bestand/Bestellungen aus STEPS-Daten",
        ],
    },
    "easyjob-because": {
        "forum_pains": [
            "Zeiterfassung für Agenturprojekte wird oft nachträglich statt tagesaktuell erledigt",
            "Ressourcenplanung bei vielen parallelen Kampagnen gilt als aufwendig zu konfigurieren",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender/Tools — jede Stunde ist Handeingabe",
            "Auswertung Ist vs. Budget je Kampagne bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in easyJOB (bcsbook-Muster)",
            "Ist-/Budget-Frühwarnung je Kampagne als Dashboard-Aufsatz",
        ],
    },
    "agorum-core": {
        "forum_pains": [
            "Konfiguration/Customizing erfordert technisches Know-how, der Community-Support ist unterschiedlich schnell",
            "Die Suche über größere Dokumentenbestände wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Reporting über Ablagequalität fehlt im Standard",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in agorum core",
            "Ablagequalitäts-Dashboard aus agorum-Metadaten",
        ],
    },
    "l-mobile": {
        "forum_pains": [
            "Konfiguration für heterogene Prozesse (Service, Lager, Produktion) erfordert Partnerunterstützung",
            "Die mobile App gilt als funktional, die Offline-Fähigkeit wird teils als verbesserungswürdig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Technikerauswahl/-Disposition nach Qualifikation/Standort",
            "Reporting über Auftragsdurchlaufzeiten bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-gestützte Disposition nach Qualifikation, Standort und SLA",
            "Durchlaufzeiten-Dashboard aus L-mobile-Daten",
        ],
    },
    "dakosy": {
        "forum_pains": [
            "Die Anbindung an ZODIAK/Zollsysteme erfordert Speditionsfachwissen und laufende Formatpflege",
            "Fehleranalyse bei abgelehnten Zollanmeldungen bleibt manuelle Fehlersuche",
        ],
        "vendor_gaps": [
            "Keine automatische Vorprüfung von Zollanmeldungen auf Plausibilität vor Absendung",
            "Reporting über Durchlaufzeiten/Ablehnungsquoten bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Vorprüfung von Zollanmeldungen auf Plausibilität vor Absendung",
            "Ablehnungsquoten-Dashboard aus DAKOSY-Daten",
        ],
    },
    "regisafe": {
        "forum_pains": [
            "Aktenplan-/Rechtekonfiguration für Verwaltungsstrukturen erfordert erhebliche Ersteinrichtung",
            "Die Bedienoberfläche wird von Sachbearbeitenden als gewöhnungsbedürftig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation eingehender Verwaltungspost",
            "Fristenüberwachung läuft teils parallel in Excel",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Verwaltungspost vor Erfassung in regisafe",
            "Automatisierte Fristenüberwachung mit Eskalation",
        ],
    },
    "rexx-systems": {
        "forum_pains": [
            "Die Modulvielfalt (Recruiting, Talent, Zeit) macht Konfiguration/Preisstruktur komplex",
            "Reporting wird für tiefere Personalkennzahlen oft in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine native KI-Bewerbervorqualifikation",
            "Fristen-/Vertragsüberwachung erfordert manuelle Kontrolle",
        ],
        "remedies": [
            "KI-gestützte Bewerbervorqualifikation als rexx-Aufsatz",
            "Automatisierte Fristen-/Vertragsüberwachung mit Eskalation",
        ],
    },
    "epg-lfs": {
        "forum_pains": [
            "Konfiguration für komplexe Lagerlayouts/Prozesse erfordert ein eigenes Integrationsprojekt",
            "Schnittstellen zu ERP/Fördertechnik erfordern laufende Pflege",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung bei Lagerprozessabweichungen",
            "Reporting über Durchsatz/Fehlerquoten bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "Anomalie-Frühwarnung als Aufsatz auf LFS-Prozessdaten",
            "Durchsatz-/Fehlerquoten-Dashboard aus LFS-Daten",
        ],
    },
    "meisterplan": {
        "forum_pains": [
            "Die Priorisierung bei sehr vielen parallelen Projekten wird als anspruchsvoll in der Konfiguration beschrieben",
            "Integration mit Zeiterfassungs-/Ticketsystemen erfordert individuelle Anbindung",
        ],
        "vendor_gaps": [
            "Keine automatische Ist-Erfassung aus Kalender/Tickets",
            "Kapazitätsengpässe werden nicht automatisch mit Frühwarnung gemeldet",
        ],
        "remedies": [
            "Automatische Ist-Zeiten-Übernahme aus Kalender/Tools in Meisterplan",
            "Kapazitätsengpass-Frühwarnung als Dashboard-Aufsatz",
        ],
    },
    "contechnet": {
        "forum_pains": [
            "Konfiguration der Module (ISO, BSI-Grundschutz, Datenschutz) erfordert Fachwissen",
            "Reporting für Managementpräsentationen wird teils extern nachbereitet",
        ],
        "vendor_gaps": [
            "Keine automatische Risikobewertung neuer Assets/Prozesse",
            "Audit-Vorbereitung bleibt teils manuelle Nachweissammlung",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus CONTECHNET-Daten für ISO 27001/BSI-Grundschutz",
            "KI-gestützte Risikobewertung neuer Assets",
        ],
    },
    "itac": {
        "forum_pains": [
            "Konfiguration für komplexe Fertigungslinien erfordert ein erhebliches Integrationsprojekt",
            "Die BDE-Bedienung gilt als funktional, aber wenig zeitgemäß",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Maschinen-/Prozessdaten",
            "OEE-Reporting bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Anomalie-/Stillstands-Frühwarnung als Aufsatz auf iTAC-Daten",
            "OEE-Dashboard aus iTAC-Daten ohne Excel-Umweg",
        ],
    },
    "planta-project": {
        "forum_pains": [
            "Konfiguration von Ressourcenplanung/Portfolios erfordert Einarbeitung, der Standard reicht selten für komplexe Multiprojektumgebungen",
            "Reporting-Vorlagen müssen oft individuell angepasst werden",
        ],
        "vendor_gaps": [
            "Keine automatische Ist-Erfassung aus Kalender/Tickets",
            "Kapazitätsauslastung über Abteilungen hinweg wird nicht automatisch aggregiert",
        ],
        "remedies": [
            "Automatische Ist-Zeiten-Übernahme aus Kalender/Tools in PLANTA (bcsbook-Muster)",
            "Auslastungs-Dashboard über Abteilungen aus PLANTA-Daten",
        ],
    },
    "matrix42": {
        "forum_pains": [
            "Konfiguration von Workflows/Kategorien für komplexere Prozesse braucht Admin-Erfahrung",
            "Das Self-Service-Portal wird von Endnutzern als wenig intuitiv empfunden",
        ],
        "vendor_gaps": [
            "Keine automatische Ticket-Vorklassifikation ohne Zusatzkonfiguration",
            "Wissensdatenbank-Pflege hängt von manueller Redaktion ab",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue",
            "Self-Service-Wissensartikel automatisch aus gelösten Matrix42-Tickets vorschlagen",
        ],
    },
    "boehme-weihs": {
        "forum_pains": [
            "Konfiguration für spezifische Fertigungs-/Qualitätsprozesse erfordert Beraterunterstützung",
            "Reporting/Statistik-Auswertung wird für Managementpräsentationen oft in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine automatische Ursachen-Clusterung bei gehäuften Reklamationen",
            "Audit-Vorbereitung bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "KI-Clusterung von Reklamationsursachen aus CASQ-it-Daten",
            "Audit-Dossier-Generator aus CASQ-it/MESQ-it-Freigabehistorie",
        ],
    },
    "scopevisio": {
        "forum_pains": [
            "Bei komplexeren Konsolidierungs-/Controlling-Anforderungen wird das System als eingeschränkt beschrieben",
            "Die Support-Reaktionszeit wird bei komplexeren Fällen als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Belegerkennung/Kontierungsvorschläge",
            "Liquiditätsplanung bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Belegerkennung mit Kontierungsvorschlägen vor Verbuchung in Scopevisio",
            "Liquiditäts-Dashboard aus Scopevisio-Daten",
        ],
    },
    "myfactory": {
        "forum_pains": [
            "Bei individuellen Prozessen stößt die Konfigurierbarkeit an Grenzen",
            "Reporting wird häufig extern in Excel nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in myfactory",
            "Bedarfsprognose-Dashboard aus myfactory-Verkaufsdaten",
        ],
    },
    "hotelkit": {
        "forum_pains": [
            "Konfiguration von Checklisten/Aufgaben für mehrere Abteilungen erfordert Ersteinrichtungsaufwand",
            "Schnittstellen zu PMS-Systemen erfordern individuelle Anbindung",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Housekeeping-/Wartungsaufgaben nach Dringlichkeit",
            "Reporting über Aufgabenqualität/Reaktionszeiten bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Priorisierung von Housekeeping-/Wartungsaufgaben nach Dringlichkeit/Gästefeedback",
            "Reaktionszeit-Dashboard aus hotelkit-Daten",
        ],
    },
    "usu": {
        "forum_pains": [
            "Konfiguration von Wissensdatenbank/Workflows erfordert erfahrene Admins",
            "Individualisierung von Reports erfordert Zusatzaufwand",
        ],
        "vendor_gaps": [
            "Keine native KI-Ticketklassifikation",
            "Wissensdatenbank-Pflege hängt von manueller Redaktion ab",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue",
            "Automatischer Wissensartikel-Vorschlag aus gelösten USU-Tickets",
        ],
    },
    "oxaion": {
        "forum_pains": [
            "Customizing erfordert Partnerunterstützung, der Standard reicht selten",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in oxaion",
            "Bedarfsprognose-Dashboard aus oxaion-Verkaufsdaten",
        ],
    },
    "jaggaer": {
        "forum_pains": [
            "Konfiguration der vielen Module (Sourcing, Contracts, Supplier) erfordert ein erhebliches Einführungsprojekt",
            "Lieferantenanbindung (Kataloge, Punch-out) erfordert individuelle Einrichtung je Lieferant",
        ],
        "vendor_gaps": [
            "Bedarfsbündelung über Abteilungen wird nicht automatisch vorgeschlagen",
            "Rechnungsabgleich bei Abweichungen erfordert manuelle Klärung",
        ],
        "remedies": [
            "Automatisierter 3-Way-Match mit KI-gestützter Abweichungsklärung",
            "Bedarfsbündelungs-Dashboard aus JAGGAER-Bestelldaten",
        ],
    },
    "sciforma": {
        "forum_pains": [
            "Konfiguration von Portfolios/Ressourcenplanung erfordert Einarbeitung",
            "Reporting-Vorlagen müssen oft individuell angepasst werden",
        ],
        "vendor_gaps": [
            "Keine automatische Ist-Erfassung aus Kalender/Tickets",
            "Kapazitätsauslastung über Abteilungen wird nicht automatisch aggregiert",
        ],
        "remedies": [
            "Automatische Ist-Zeiten-Übernahme aus Kalender/Tools in Sciforma",
            "Auslastungs-Dashboard über Abteilungen aus Sciforma-Daten",
        ],
    },
    "tisoware": {
        "forum_pains": [
            "Konfiguration komplexer Zeitmodelle/Zutrittsregeln erfordert Spezialwissen",
            "Der Self-Service für Mitarbeitende gilt als funktional, aber nicht immer intuitiv",
        ],
        "vendor_gaps": [
            "Keine automatische Schichtvorschlags-KI",
            "Auswertung von Fehlzeitenmustern für Frühwarnung fehlt im Standard",
        ],
        "remedies": [
            "Fehlzeiten-/Auslastungs-Frühwarnung als Dashboard-Aufsatz auf tisoware-Daten",
            "KI-gestützte Schichtvorschläge auf Basis von Bedarf und Qualifikation",
        ],
    },
    "selectline": {
        "forum_pains": [
            "Bei individuellen Prozessen stößt die Konfigurierbarkeit an Grenzen, es braucht Partnerlösungen",
            "Reporting wird häufig extern in Excel nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in SelectLine",
            "Bedarfsprognose-Dashboard aus SelectLine-Verkaufsdaten",
        ],
    },
    "caralegal": {
        "forum_pains": [
            "Konfiguration von VVT-/DSFA-Vorlagen für komplexe Organisationen erfordert Fachwissen",
            "Integration mit bestehenden IT-/HR-Systemen erfordert individuelle Anbindung",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung neuer meldepflichtiger Verarbeitungen aus operativen Systemen",
            "Audit-Vorbereitung bleibt teils manuelle Nachweissammlung trotz Tool",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus caralegal-Daten für DSGVO-/KI-VO-Nachweise",
            "Automatische Erkennung neuer Verarbeitungstätigkeiten aus IT-Systemveränderungen",
        ],
    },
    "windream": {
        "forum_pains": [
            "Konfiguration von Ablagestrukturen/Rechten erfordert Partner-Know-how",
            "Die Suche über große Dokumentenbestände wird bei Wachstum langsamer",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Reporting über Ablagequalität fehlt im Standard",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in windream",
            "Ablagequalitäts-Dashboard aus windream-Metadaten",
        ],
    },
    "dvinci": {
        "forum_pains": [
            "Individualisierung von Karriereseiten/Formularen erfordert technisches Know-how",
            "Kandidatensuche/-filterung gilt als weniger komfortabel als bei spezialisierten Tools",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorqualifikation von Bewerbungen",
            "Reporting über Recruiting-Funnel-Qualität bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-gestützte Bewerbervorqualifikation/Matching als d.vinci-Aufsatz",
            "Recruiting-Funnel-Dashboard aus d.vinci-Daten",
        ],
    },
    "gus-os": {
        "forum_pains": [
            "Customizing für Prozessindustrie-Spezifika erfordert ein erhebliches Einführungsprojekt",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in GUS-OS",
            "Bedarfsprognose-Dashboard aus GUS-OS-Verkaufsdaten",
        ],
    },
    "timetac": {
        "forum_pains": [
            "Bei komplexeren Zeitmodellen (Gleitzeit, Schicht, mehrere Standorte) wird die Konfiguration als aufwendig beschrieben",
            "Die mobile Erfassung wird gelegentlich als fehleranfällig bei GPS/Verbindung genannt",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender/Tools — jede Stunde ist Handeingabe",
            "Auswertung von Überstundenmustern bleibt Basis-Reporting",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in TimeTac (bcsbook-Muster)",
            "Überstunden-Frühwarnung als Dashboard-Aufsatz auf TimeTac-Daten",
        ],
    },
    "dampsoft": {
        "forum_pains": [
            "Die Abrechnung (GOZ/BEMA) erfordert regelmäßige manuelle Prüfung bei Ablehnungen",
            "Terminplanung bei mehreren Behandlern/Stühlen gilt als konfigurationsaufwendig",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Abrechnung vor der Einreichung",
            "Recall-/Erinnerungsmanagement läuft teils parallel manuell",
        ],
        "remedies": [
            "Plausibilitätscheck der GOZ/BEMA-Abrechnung vor Einreichung",
            "Automatisiertes Recall-/Erinnerungsmanagement als DS-Win-Aufsatz",
        ],
    },
    "pit-fm": {
        "forum_pains": [
            "Konfiguration von Flächen-/Wartungsdaten für große Portfolios erfordert erheblichen Ersteinrichtungsaufwand",
            "Die mobile Erfassung vor Ort wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Störmeldungen nach Kritikalität",
            "Prüffristen-Reporting für Auditoren bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Priorisierung eingehender Störmeldungen nach Kritikalität",
            "Automatisiertes Prüffristen-Dossier aus pit-FM-Daten",
        ],
    },
    "insiders-technologies": {
        "forum_pains": [
            "Die Ersteinrichtung/das Training der Erkennung für spezifische Belegformate erfordert Projektaufwand",
            "Ausnahmefälle landen trotzdem in manueller Nachbearbeitung",
        ],
        "vendor_gaps": [
            "Trefferquote bei untypischen/handschriftlichen Belegen bleibt begrenzt ohne Nachtraining",
            "Reporting über Erkennungsqualität/Ausnahmequote bleibt Basis-Auswertung",
        ],
        "remedies": [
            "Laufendes KI-Nachtraining der Belegerkennung auf eigene Ausnahmefälle",
            "Erkennungsqualitäts-Dashboard aus smart-INVOICE-Daten",
        ],
    },
    "facilioo": {
        "forum_pains": [
            "Die Ticketflut aus Mieteranfragen bei größeren Portfolios wird als schwer priorisierbar beschrieben",
            "Integration mit Bestandsverwaltungssoftware erfordert bei manchen Kombinationen manuelle Nacharbeit",
        ],
        "vendor_gaps": [
            "Keine automatische Vorklassifikation eingehender Mieteranfragen",
            "Reporting über Reaktionszeiten bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Vorklassifikation eingehender facilioo-Anfragen nach Dringlichkeit",
            "SLA-/Reaktionszeit-Dashboard aus facilioo-Daten",
        ],
    },
    "ra-micro": {
        "forum_pains": [
            "Die Umstellung von Altversionen/Modulen erfordert erhebliche Migrationsarbeit",
            "Die Bedienoberfläche gilt als funktional, aber wenig modern im Vergleich zu neueren Kanzleitools",
        ],
        "vendor_gaps": [
            "Fristenkontrolle läuft teils parallel in Outlook/Excel statt vollständig im System",
            "Dokumentenklassifikation eingehender Post erfolgt manuell",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Kanzleipost vor Erfassung in RA-MICRO",
            "Automatisierte Fristenüberwachung mit Eskalation statt Parallelpflege in Outlook",
        ],
    },
    "comarch-erp-enterprise": {
        "forum_pains": [
            "Customizing für Sonderprozesse erfordert ein erhebliches Einführungsprojekt",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine native KI-Bedarfsprognose",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in Comarch ERP Enterprise",
            "Bedarfsprognose-Dashboard aus Comarch-Verkaufsdaten",
        ],
    },
    "theorg-sovdwaer": {
        "forum_pains": [
            "Terminplanung bei mehreren Therapeuten/Standorten gilt als konfigurationsaufwendig",
            "Abrechnung mit Kassen/Selbstzahlern erfordert manuelle Nachbearbeitung bei Rückfragen",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Abrechnung vor der Einreichung",
            "Recall-/Wartelisten-Management läuft teils parallel manuell",
        ],
        "remedies": [
            "Plausibilitätscheck der Abrechnung vor Einreichung",
            "Automatisiertes Wartelisten-/Recall-Management als THEORG-Aufsatz",
        ],
    },
    "medifox-dan": {
        "forum_pains": [
            "Der Dokumentationsaufwand in der ambulanten/stationären Pflege bleibt trotz Software hoch",
            "Tourenplanung bei kurzfristigen Ausfällen erfordert viel manuelle Nachplanung",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Leistungsdokumentation vor der Abrechnung",
            "Tourenoptimierung nach Verfügbarkeit/Qualifikation ist nicht KI-gestützt",
        ],
        "remedies": [
            "Plausibilitätscheck der Pflegedokumentation vor Abrechnungslauf",
            "KI-gestützte Tourenoptimierung als MD-Ambulant-Aufsatz",
        ],
    },
    "wilken": {
        "forum_pains": [
            "Releasewechsel und Anpassung an regulatorische Änderungen erfordern erheblichen Testaufwand",
            "Konfiguration branchenspezifischer Prozesse erfordert Spezialwissen",
        ],
        "vendor_gaps": [
            "Keine automatische Fehleranalyse bei gescheiterten Marktkommunikations-/Abrechnungsprozessen",
            "Reporting für Regulatorik-Meldungen wird oft in Excel nachbereitet",
        ],
        "remedies": [
            "Automatisiertes Fehler-Monitoring für Abrechnungs-/Marktprozesse mit Klartext-Ursache",
            "Regulatorik-Reporting-Aufsatz aus Wilken-Daten",
        ],
    },
    "caq-ag": {
        "forum_pains": [
            "Konfiguration von FMEA-/Reklamationsprozessen erfordert erfahrene QM-Admins",
            "Reporting/Statistik-Auswertung wird für Managementpräsentationen oft in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine automatische Ursachen-Clusterung bei gehäuften Reklamationen",
            "Audit-Vorbereitung bleibt manuelle Nachweissammlung",
        ],
        "remedies": [
            "KI-Clusterung von Reklamationsursachen aus CAQ.Net-Daten",
            "Audit-Dossier-Generator aus CAQ.Net-Freigabehistorie",
        ],
    },
    "serviceware": {
        "forum_pains": [
            "Konfiguration der Module (Knowledge, Processes, Financial) erfordert ein erhebliches Einführungsprojekt",
            "Die Wissensdatenbank-Pflege hängt stark von manueller Redaktion ab",
        ],
        "vendor_gaps": [
            "Keine native KI-Ticketklassifikation",
            "Reporting für Management-KPIs erfordert zusätzliche Konfiguration",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue",
            "Automatischer Wissensartikel-Vorschlag aus gelösten Serviceware-Tickets",
        ],
    },
    "ibi-systems-iris": {
        "forum_pains": [
            "Konfiguration der Module für ISMS/Grundschutz/Datenschutz erfordert Fachwissen und Zeit",
            "Reporting für Managementpräsentationen wird teils extern nachbereitet",
        ],
        "vendor_gaps": [
            "Keine automatische Risikobewertung neuer Assets/Prozesse",
            "Audit-Vorbereitung bleibt teils manuelle Nachweissammlung",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus i-doit/iris-Daten für ISO 27001/BSI-Grundschutz",
            "KI-gestützte Risikobewertung neuer Assets/Prozesse",
        ],
    },
    "imsware": {
        "forum_pains": [
            "Konfiguration von Flächen-/Wartungsdaten für große Portfolios erfordert erheblichen Ersteinrichtungsaufwand",
            "Die mobile Erfassung vor Ort wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Störmeldungen nach Kritikalität",
            "Prüffristen-Reporting für Auditoren bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Priorisierung eingehender Störmeldungen nach Kritikalität",
            "Automatisiertes Prüffristen-Dossier aus IMSWARE-Daten",
        ],
    },
    "solutio-charly": {
        "forum_pains": [
            "Die Abrechnung (GOZ/BEMA) erfordert regelmäßige manuelle Prüfung bei Ablehnungen",
            "Terminplanung bei mehreren Behandlern gilt als konfigurationsaufwendig",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Abrechnung vor der Einreichung",
            "Recall-/Erinnerungsmanagement läuft teils parallel manuell",
        ],
        "remedies": [
            "Plausibilitätscheck der GOZ/BEMA-Abrechnung vor Einreichung",
            "Automatisiertes Recall-/Erinnerungsmanagement als charly-Aufsatz",
        ],
    },
    "corporate-planning": {
        "forum_pains": [
            "Die Modellierung komplexer Planungsmodelle erfordert Controlling-/Excel-Erfahrung",
            "Datenanbindung an Vorsysteme erfordert individuelle ETL-Pflege",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Planzahlen",
            "Ad-hoc-Analysen werden häufig extern in Excel nachgezogen",
        ],
        "remedies": [
            "Automatisierte Abweichungs-/Anomalie-Erkennung in CP-Suite-Planzahlen",
            "ETL-Konnektor CP-Suite↔Vorsysteme als wiederverwendbare Standardbrücke",
        ],
    },
    "fabasoft": {
        "forum_pains": [
            "Konfiguration von Ablagestrukturen/Workflows für Verwaltungsprozesse erfordert Partner-Know-how",
            "Die Suche über große Aktenbestände wird bei Wachstum langsamer",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Reporting über Vertragsfristen/Ablagequalität fehlt im Standard",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in Fabasoft",
            "Automatisierte Vertragsfristen-Überwachung mit Eskalation",
        ],
    },
    "isgus-zeus": {
        "forum_pains": [
            "Konfiguration komplexer Zeitmodelle/Zutrittsregeln erfordert Spezialwissen",
            "Der Self-Service für Mitarbeitende gilt als funktional, aber nicht immer intuitiv",
        ],
        "vendor_gaps": [
            "Keine automatische Schichtvorschlags-KI",
            "Auswertung von Fehlzeitenmustern für Frühwarnung fehlt im Standard",
        ],
        "remedies": [
            "Fehlzeiten-/Auslastungs-Frühwarnung als Dashboard-Aufsatz auf ZEUS-Daten",
            "KI-gestützte Schichtvorschläge auf Basis von Bedarf und Qualifikation",
        ],
    },
    "dataguard": {
        "forum_pains": [
            "Onboarding und Konfiguration der Plattform für die eigene Organisation erfordern Zeit und externe Beratung",
            "Individuelle Prozesse (Sonderfälle bei Verarbeitungen) passen nicht immer direkt in die Standardvorlagen",
        ],
        "vendor_gaps": [
            "Keine automatische Erkennung neuer meldepflichtiger Verarbeitungen aus operativen Systemen",
            "Audit-Vorbereitung bleibt teils manuelle Nachweissammlung trotz Plattform",
        ],
        "remedies": [
            "Audit-Dossier-Generator aus DataGuard-Daten für DSGVO-/ISO-Nachweise",
            "Automatische Erkennung neuer Verarbeitungstätigkeiten aus IT-Systemveränderungen",
        ],
    },
    "sihot": {
        "forum_pains": [
            "Konfiguration für mehrere Häuser/Ratenpläne erfordert erhebliche Ersteinrichtung",
            "Schnittstellen zu Channel-Managern/OTAs erfordern laufende Pflege",
        ],
        "vendor_gaps": [
            "Keine automatische Preisoptimierung/Revenue-Management ohne Zusatzmodul",
            "Reporting über Belegungs-/Ertragskennzahlen bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Revenue-/Preisoptimierungs-Aufsatz auf SIHOT-Belegungsdaten",
            "Ertrags-Dashboard aus SIHOT-Daten ohne Excel-Umweg",
        ],
    },
    "kisters": {
        "forum_pains": [
            "Konfiguration branchenspezifischer Prozesse (Messwesen, Abrechnung) erfordert Spezialwissen",
            "Releasewechsel und regulatorische Anpassungen erfordern erheblichen Testaufwand",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Messdaten",
            "Reporting für Regulatorik-Meldungen wird oft in Excel nachbereitet",
        ],
        "remedies": [
            "Anomalie-Frühwarnung als Aufsatz auf KISTERS-Messdaten",
            "Regulatorik-Reporting-Aufsatz aus KISTERS-Daten",
        ],
    },
    "streit-software": {
        "forum_pains": [
            "Die mobile Auftragsbearbeitung für Monteure im Feld wird als ausbaufähig beschrieben",
            "Stammdatenpflege (Material, Preise) erfordert regelmäßigen manuellen Aufwand",
        ],
        "vendor_gaps": [
            "Keine automatische Angebots-/Rechnungsprüfung gegen erfasste Aufmaße",
            "Reporting über Auftragsrentabilität bleibt Excel-Auswertung",
        ],
        "remedies": [
            "KI-Abgleich Aufmaß vs. Rechnung vor Freigabe",
            "Rentabilitäts-Dashboard je Auftrag aus STREIT-V.1-Daten",
        ],
    },
    "spie-rodias": {
        "forum_pains": [
            "Konfiguration von Anlagenstrukturen/Wartungsplänen für heterogene Anlagenparks erfordert erheblichen Ersteinrichtungsaufwand",
            "Die mobile Erfassung von Wartungsnachweisen vor Ort wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Priorisierung von Störmeldungen nach Kritikalität",
            "Prüffristen-Reporting für Auditoren bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-Priorisierung eingehender Störmeldungen nach Kritikalität",
            "Automatisiertes Prüffristen-Dossier aus openTALOS-Daten",
        ],
    },
    "factro": {
        "forum_pains": [
            "Bei wachsenden Teams/Projektstrukturen wird die Übersichtlichkeit als eingeschränkt beschrieben",
            "Zeiterfassung wird teils als nachträgliche Pflicht statt tagesaktueller Routine beschrieben",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender/Tickets",
            "Reporting über Ist vs. Budget bleibt Basis-Auswertung",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in factro (bcsbook-Muster)",
            "Ist-/Budget-Dashboard als Aufsatz auf factro-Daten",
        ],
    },
    "umantis": {
        "forum_pains": [
            "Individualisierung von Bewerbungsformularen/Prozessen erfordert technisches Know-how",
            "Kandidatensuche gilt als weniger komfortabel als bei spezialisierten ATS",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorqualifikation von Bewerbungen",
            "Reporting über Recruiting-Funnel-Qualität bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-gestützte Bewerbervorqualifikation/Matching als Umantis-Aufsatz",
            "Recruiting-Funnel-Dashboard aus Umantis-Daten",
        ],
    },
    "can-do": {
        "forum_pains": [
            "Konfiguration von Ressourcenplanung/Portfolios erfordert Einarbeitung",
            "Integration mit Zeiterfassungssystemen erfordert individuelle Anbindung",
        ],
        "vendor_gaps": [
            "Keine automatische Ist-Erfassung aus Kalender/Tickets",
            "Kapazitätsengpässe werden nicht automatisch mit Frühwarnung gemeldet",
        ],
        "remedies": [
            "Automatische Ist-Zeiten-Übernahme aus Kalender/Tools in Can Do",
            "Kapazitätsengpass-Frühwarnung als Dashboard-Aufsatz",
        ],
    },
    "veda": {
        "forum_pains": [
            "Konfiguration von Genehmigungsworkflows bei wachsender Mitarbeiterzahl wird unübersichtlich",
            "Reporting-Funktionen gelten als Basis, tiefere Personalkennzahlen werden in Excel nachgebaut",
        ],
        "vendor_gaps": [
            "Keine automatische Vertragsfristen-/Probezeit-Überwachung mit proaktiver Eskalation",
            "Onboarding-Checklisten müssen manuell an jede Rolle angepasst werden",
        ],
        "remedies": [
            "Automatisierte Fristen-/Probezeit-Überwachung mit Eskalationsmail",
            "HR-Kennzahlen-Dashboard aus VEDA-Daten",
        ],
    },
    "amagno": {
        "forum_pains": [
            "Konfiguration von Ablagestrukturen/Rechten erfordert Einarbeitung",
            "Die Suche über größere Dokumentenbestände wird als ausbaufähig beschrieben",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Reporting über Ablagequalität fehlt im Standard",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in AMAGNO",
            "Ablagequalitäts-Dashboard aus AMAGNO-Metadaten",
        ],
    },
    "domus-software": {
        "forum_pains": [
            "Bei komplexen Portfolios wird die Konfiguration als anspruchsvoll beschrieben",
            "Betriebskostenabrechnung erfordert manuelle Prüfung bei Abweichungen",
        ],
        "vendor_gaps": [
            "Keine automatische Klassifikation eingehender Post",
            "Mängelmanagement läuft teils parallel per E-Mail",
        ],
        "remedies": [
            "KI-Eingangspost-Klassifikation vor Erfassung in DOMUS",
            "Automatisierte Plausibilitätsprüfung der Betriebskostenabrechnung",
        ],
    },
    "candis": {
        "forum_pains": [
            "Ausnahmefälle (unklare Zuordnung, Sonderformate) landen trotzdem in manueller Klärung",
            "Freigabeworkflows bei komplexen Kostenstellenstrukturen erfordern Ersteinrichtung",
        ],
        "vendor_gaps": [
            "Trefferquote bei untypischen Belegformaten bleibt begrenzt ohne Nachtraining",
            "Reporting über Durchlaufzeiten im Freigabeprozess bleibt Basis-Auswertung",
        ],
        "remedies": [
            "KI-Nachtraining der Belegerkennung auf eigene Lieferantenformate",
            "Durchlaufzeiten-Dashboard für den CANDIS-Freigabeprozess",
        ],
    },
    "troi": {
        "forum_pains": [
            "Zeiterfassung für Agenturprojekte wird oft nachträglich statt tagesaktuell erledigt",
            "Ressourcenplanung bei vielen parallelen Kampagnen gilt als aufwendig zu konfigurieren",
        ],
        "vendor_gaps": [
            "Keine automatische Buchung aus Kalender/Tools",
            "Auswertung Ist vs. Budget je Kampagne bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Automatische Buchungsvorschläge aus Kalender/Tools in Troi (bcsbook-Muster)",
            "Ist-/Budget-Frühwarnung je Kampagne als Dashboard-Aufsatz",
        ],
    },
    "cargo-support": {
        "forum_pains": [
            "Disposition bei kurzfristigen Änderungen erfordert viel manuelle Nachplanung",
            "Schnittstellen zu Kunden-/Frachtführerportalen erfordern individuelle Anpassung",
        ],
        "vendor_gaps": [
            "Keine automatische Frachtführerauswahl nach Preis/Verfügbarkeit/Historie",
            "Track-and-Trace-Kommunikation an Kunden läuft teils manuell",
        ],
        "remedies": [
            "Automatisierte Frachtführer-Empfehlung aus cs-CONNECT-Historiendaten",
            "Automatisches Track-and-Trace-Kundenupdate aus cs-CONNECT-Statusdaten",
        ],
    },
    "lis-winsped": {
        "forum_pains": [
            "Konfiguration für komplexe Speditionsprozesse erfordert Fachwissen und Einarbeitungszeit",
            "Schnittstellen zu Kunden-/Partnersystemen erfordern laufende Pflege",
        ],
        "vendor_gaps": [
            "Keine automatische Frachtführer-/Tourenoptimierung nach Preis/Verfügbarkeit",
            "Reporting über Durchlaufzeiten/Abweichungen bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-gestützte Touren-/Frachtführeroptimierung als WinSped-Aufsatz",
            "Durchlaufzeiten-Dashboard aus WinSped-Daten",
        ],
    },
    "zammad": {
        "forum_pains": [
            "Konfiguration von Automatisierungsregeln/Triggern erfordert Einarbeitung, der Standard reicht selten für komplexe Prozesse",
            "Reporting-Funktionen gelten als solide, aber für tiefere KPI-Analysen wird oft extern ausgewertet",
        ],
        "vendor_gaps": [
            "Keine native KI-Ticketklassifikation im Kern, die Priorisierung bleibt regelbasiert",
            "Wissensdatenbank-Pflege hängt von manueller Redaktion ab",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Tickets vor der Queue",
            "Automatischer Wissensartikel-Vorschlag aus gelösten Zammad-Tickets",
        ],
    },
    "simba": {
        "forum_pains": [
            "Die Bedienoberfläche gilt als funktional, aber wenig modern im Vergleich zu neueren Kanzleitools",
            "Schnittstellen zu Vorsystemen erfordern individuelle Anpassung",
        ],
        "vendor_gaps": [
            "Fristenkontrolle läuft teils parallel in Outlook/Excel",
            "Dokumentenklassifikation eingehender Post erfolgt manuell",
        ],
        "remedies": [
            "KI-Klassifikation eingehender Post vor Erfassung in Simba",
            "Automatisierte Fristenüberwachung mit Eskalation",
        ],
    },
    "stp-lexolution": {
        "forum_pains": [
            "Konfiguration von Ablagestrukturen/Workflows für Kanzleiprozesse erfordert Partner-Know-how",
            "Die Suche über große Aktenbestände wird bei Wachstum langsamer",
        ],
        "vendor_gaps": [
            "Keine native KI-Vorverschlagwortung eingehender Dokumente",
            "Fristenüberwachung läuft teils parallel in Excel/Outlook",
        ],
        "remedies": [
            "KI-Vorverschlagwortung eingehender Dokumente vor Ablage in LEXolution.DMS",
            "Automatisierte Fristenüberwachung mit Eskalation",
        ],
    },
    "pharmatechnik-ixos": {
        "forum_pains": [
            "Die Bedienoberfläche an der Kasse gilt als funktional, aber wenig modern",
            "Bestellwesen/Lagerabgleich bei knappen Lieferengpässen erfordert manuelle Nacharbeit",
        ],
        "vendor_gaps": [
            "Keine automatische Bedarfsprognose für Nachbestellungen",
            "Reporting über Umsatz-/Lagerkennzahlen bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Bedarfsprognose-Dashboard aus IXOS-Verkaufsdaten",
            "Automatisierte Lagerabgleich-/Bestellvorschlags-Logik als IXOS-Aufsatz",
        ],
    },
    "csb-system": {
        "forum_pains": [
            "Customizing für branchenspezifische Prozesse (Chargenrückverfolgung) erfordert ein erhebliches Projekt",
            "Reporting wird häufig extern nachgezogen",
        ],
        "vendor_gaps": [
            "Keine automatische Anomalieerkennung in Produktions-/Qualitätsdaten",
            "Rechnungseingang ohne Zusatzmodul bleibt manuelle Erfassung",
        ],
        "remedies": [
            "KI-Rechnungserkennung vor Verbuchung in CSB-System",
            "Anomalie-Dashboard für Produktions-/Chargendaten aus CSB-System",
        ],
    },
    "pi-loga": {
        "forum_pains": [
            "Konfiguration von Gehaltsarten/Regelwerken erfordert Spezialwissen, Partnerunterstützung ist meist nötig",
            "Das Self-Service-Portal für Mitarbeitende gilt als funktional, aber nicht immer modern",
        ],
        "vendor_gaps": [
            "Keine automatische Plausibilitätsprüfung der Abrechnungsdaten vor dem Lauf",
            "Reporting für Personalkennzahlen bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Plausibilitätscheck der Abrechnungsdaten vor dem LOGA-Lauf",
            "HR-Kennzahlen-Dashboard aus P&I-LOGA-Daten",
        ],
    },
    "awinta": {
        "forum_pains": [
            "Bestellwesen/Lagerabgleich bei Lieferengpässen erfordert manuelle Nacharbeit",
            "Schnittstellen zu Kassensystemen/Rezeptabrechnung erfordern laufende Pflege",
        ],
        "vendor_gaps": [
            "Keine automatische Bedarfsprognose für Nachbestellungen",
            "Reporting über Umsatz-/Lagerkennzahlen bleibt teils Excel-Nacharbeit",
        ],
        "remedies": [
            "Bedarfsprognose-Dashboard aus awintaONE-Verkaufsdaten",
            "Automatisierte Lagerabgleich-/Bestellvorschlags-Logik",
        ],
    },
    "untis": {
        "forum_pains": [
            "Erstellung/Änderung komplexer Stundenpläne bei Vertretungsfällen erfordert erhebliche manuelle Nacharbeit",
            "Die Bedienoberfläche gilt für Gelegenheitsnutzer (Lehrkräfte) als wenig intuitiv",
        ],
        "vendor_gaps": [
            "Keine automatischen Vertretungsplanvorschläge nach Verfügbarkeit/Qualifikation",
            "Reporting über Unterrichtsausfall/Vertretungsquote bleibt Excel-Nacharbeit",
        ],
        "remedies": [
            "KI-gestützte Vertretungsplanvorschläge nach Verfügbarkeit und Qualifikation",
            "Ausfall-/Vertretungsquoten-Dashboard aus Untis-Daten",
        ],
    },
}


def entry_for(catalog_id: str) -> dict | None:
    """Return the gap-research entry for a catalog_id, or None if unknown."""
    return GAP_RESEARCH.get(catalog_id)


def all_ids() -> frozenset[str]:
    """Return the set of catalog_ids covered by this module."""
    return frozenset(GAP_RESEARCH.keys())
