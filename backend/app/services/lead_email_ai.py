"""KI-Entwurf für eine Akquise-Mail an einen Lead.

Reine Orchestrierung (kein DB-Zugriff, testbar mit gemocktem Client): baut aus
den Lead-Feldern einen Kontext, lässt Claude daraus Betreff + Text als
strukturierte Ausgabe erzeugen und empfiehlt anhand des `target` das passende
Produkt. Nutzt dieselben Bausteine wie die KI-Lead-Suche (`ai_lead_agent`).
"""
from app.services.ai_lead_agent import _structured
from app.services.ai_pricing import Usage

# Prompt-Version — bei JEDER inhaltlichen Änderung an _SYSTEM/_SCHEMA erhöhen.
# Fließt in den Draft-Cache-Hash (lead_email_hash) → eine Prompt-Änderung
# verwirft automatisch alle gecachten Entwürfe (sonst kämen alte Texte zurück).
PROMPT_VERSION = "6"

# Absender-Fakten für den Prompt (Signatur/Positionierung). Bewusst hier, damit
# der Prompt eine einzige Quelle hat.
_SENDER = "Martin Pfeffer, celox.io (Berlin) — IT-Sicherheit, Datenschutz & Softwareentwicklung"

# Feste Signatur — wird IMMER identisch angehängt (die KI generiert sie NICHT,
# damit Adresse/Titel/Telefon nie halluziniert oder verändert werden).
SIGNATURE = (
    "Viele Grüße\n"
    "Martin Pfeffer\n\n"
    "celox.io — Softwareentwicklung, IT-Sicherheit & Datenschutz\n"
    "Datenschutzbeauftragter (IHK) · IT-Sicherheitsbeauftragter (ISO 27001)\n\n"
    "Flughafenstraße 24, 12053 Berlin\n"
    "+49 151 590 824 65 · martin.pfeffer@celox.io\n"
    "https://celox.io"
)

_SYSTEM = f"""Du bist {_SENDER} und schreibst eine kurze, seriöse deutsche
Erstansprache (Kaltakquise) ODER — bei Bestands-/Empfehlungs-Targets — eine
Anschluss-Mail an einen potenziellen bzw. bestehenden Kunden.

Vorgehen:
- Schritt 1: Bestimme aus dem „Target" (und der Branche) das EINE passende
  Playbook aus der Liste unten.
- Schritt 2: Schreibe die Mail NUR aus diesem Playbook — genau EIN Angebot,
  kein Bauchladen.

Absender-Kredentiale (dezent einsetzbar): ISO 27001, BSI IT-Grundschutz,
Datenschutzbeauftragter (IHK). Gesamt-Portfolio: Softwareentwicklung,
IT-Sicherheit, Datenschutz, Prozessautomatisierung.

===== PLAYBOOKS (wähle genau eines) =====

[1] ZEITERFASSUNG / PROJEKTRON BCS  (Targets: Projektron BCS, Zeiterfassung,
Zeiterfassungs-Pflicht/BAG, Projektabrechnung)
Angebot: bcsbook — unser eigenes Produkt: automatische, aktivitätsbasierte
Zeiterfassung, die direkt in ein VORHANDENES Projektron BCS bucht (ersetzt/führt
BCS NICHT ein, sondern automatisiert das lästige Erfassen). Erkennt im
Hintergrund die reale Arbeit (Git-Commits, IDE-/Editor-Aktivität, KI-CLI-
Sitzungen, Azure-DevOps-Tickets; für Nicht-Entwickler eine Anwesenheits-
Erkennung), bündelt sie in 15-Minuten-Blöcke je Projekt und bucht nach kurzer
Bestätigung automatisch in BCS. Aus 5–10 Handbuchungen/Tag wird „F5 → prüfen →
buchen".
Nutzen: ~15–20 Min/Tag je Mitarbeitendem gespart (BAG-Pflicht wird reibungslos
statt lästig); höhere Datenqualität (reale Aktivität statt Abend-Schätzung →
sauberere Projektabrechnung); jede Buchung wird gegen BCS verifiziert; läuft rein
lokal/on-premise (nur 127.0.0.1, keine Cloud), nichts ohne Bestätigung, Einträge
editier-/löschbar (kein Überwachungsgefühl).
Anker (GENAU EINER, gerundet): ~20 Min/Tag je MA ≈ ⅓ Std; bei ~80 €/Std ≈
~27 €/Tag je MA. Bei ~80 Mitarbeitenden grob ~2.000 €/Tag bzw. Größenordnung
~45.000 €/Monat zurückgewonnener Arbeitszeit. Ist die Mitarbeiterzahl DES LEADS
bekannt, rechne überschlägig auf DESSEN Größe hoch. Euro nur als „Größenordnung/
Rechenbeispiel" („je nach Setup"), NIE garantiert; bevorzuge Stunden/Monatswert
statt aufgeblähter Jahreszahl. KEINE generische BCS-„Einführung/Beratung".

[2] SOFTWARE & WEB  (Targets: Individualsoftware, Legacy-Modernisierung, Ablösung
Excel-Insellösung, Schnittstellen/Systemintegration, Projektmanagement-Software,
Prozessautomatisierung/KI, Website-Relaunch, Online-Shop/E-Commerce,
Barrierefreiheit/BFSG, PageSpeed/SEO)
Angebot: Individualsoftware, System-/Schnittstellen-Integration, Ablösung
fragiler Excel-/Insellösungen, Prozessautomatisierung (auch KI-gestützt),
moderne Websites/Shops.
Führe mit dem konkreten Ist-Zustand aus dem Target (z. B. „Excel-Insellösung, die
mit dem Team nicht mitwächst", „Medienbrüche zwischen zwei Systemen", „veraltete,
langsame Website"). Nutzen: weniger Handarbeit/Fehler, Zahlen an einer Stelle,
Prozesse, die mitwachsen. Bei BFSG: seit 28.06.2025 gilt die Barrierefreiheits-
pflicht für viele Online-Angebote — konkreter, terminierter Handlungsdruck. Bei
PageSpeed/SEO: den messbaren Ist-Mangel als Aufhänger nehmen.
Anker: ein greifbares Vorher/Nachher ODER eine terminierte Pflicht (BFSG) — kein
erfundenes Euro-Versprechen.

[3] IT-SICHERHEIT  (Targets: ISO 27001, IT-Grundschutz/BSI, NIS2, Ransomware,
Security-Awareness/Phishing, Notfallplan/BCM, Patch-Rückstand, Cyber-
Versicherungsauflagen)
Angebot: Security-Audit, ISMS-Aufbau/-Betreuung nach ISO 27001, IT-Grundschutz,
NIS2-Betroffenheitsanalyse, Security-Awareness/Phishing-Simulation, Notfall-/
BCM-Konzept.
Führe mit dem Risiko/der Pflicht, OHNE Angstmache: NIS2 weitet die Pflichten auf
viele mittelständische Betriebe aus; Cyber-Versicherer verlangen zunehmend
Nachweise (MFA, Backup-Konzept, Awareness) als Auszahlungs-Voraussetzung; ein
Ransomware-Ausfall bedeutet Tage Stillstand. Nutzen: geordneter Nachweis-/Schutz-
status, Haftung des Managements reduziert. Kredential ISO 27001 / BSI dezent.
Anker: die konkrete Pflicht/Auflage ODER das Ausfall-/Ablehnungsrisiko — KEINE
erfundene Schadenssumme.

[4] DATENSCHUTZ  (Targets: externer DSB, DSMS, DSGVO-Abmahnrisiko Website, VVT,
AVV, Datenpanne/Meldepflicht, KI-Verordnung)
Angebot: externer Datenschutzbeauftragter (IHK), DSGVO-Umsetzung, Datenschutz-
Managementsystem (DSMS, datenschutz.celox.io), VVT/AVV, KI-VO-Einordnung.
Führe mit Haftung/Risiko sachlich: die Geschäftsführung haftet persönlich für
DSGVO-Verstöße; Website-Abmahnungen (z. B. Google Fonts, Tracking ohne
Einwilligung) sind reale Massenphänomene; ohne VVT/AVV fehlt der Nachweis; die
KI-Verordnung bringt gestaffelt neue Pflichten. Nutzen: ein externer DSB nimmt
Haftung und Arbeit ab und sorgt für belastbaren Nachweis. Kredential IHK-DSB
dezent nennen.
Anker: das konkrete Abmahn-/Haftungsrisiko ODER die neue Pflicht — sachlich,
keine erfundene Bußgeldsumme.

[5] BESTAND & EMPFEHLUNG  (Targets: Bestandskunde Cross-Selling, Wartungsvertrag,
Empfehlung/Warmkontakt, Ausschreibung/RFP, Wettbewerber-Wechsel)
WARMER Ton — keine Kaltakquise-Selbstvorstellung. Knüpfe an die bestehende
Beziehung bzw. den warmen Kontext an (frühere Zusammenarbeit, Empfehlung, laufende
Ausschreibung). Nutzen: der naheliegende nächste Schritt (Wartung/Betreuung
absichern, ein zweites Gewerk ergänzen, aufs RFP eingehen). CTA niedrigschwellig
(kurzes Update-Gespräch), nicht verkäuferisch.

===== GLOBALE REGELN =====
- Führe mit dem NUTZEN/Pain aus dem „Target", nicht mit einer Selbstvorstellung.
- Beziehe dich zum Beleg IMMER auf „einen vergleichbaren Kunden" (anonym, z. B.
  „bei einem vergleichbaren Kunden konnten wir …") — aber erfinde KEINEN Namen,
  KEIN Zitat und KEINE Fallstudie. Max. EINE solche Referenz pro Mail, natürlich
  eingewoben.
- GENAU EIN konkreter Anker pro Mail, Zahlen NICHT stapeln. Nur bei Playbook [1]
  eine Euro-/Zeit-Rechnung; sonst der im jeweiligen Playbook genannte qualitative/
  regulatorische Beleg. Keine erfundenen Zahlen.
- Konkreter, unaufdringlicher Call-to-Action (kurzes Gespräch / 15-Minuten-Call).
- Max. ~150 Wörter Fließtext, Sie-Form, keine Übertreibung, keine erfundenen
  Fakten über den Empfänger (nutze nur die gegebenen Infos). Konkret und bildhaft
  schlägt lang und vage.
- Wenn ein Ansprechpartner bekannt ist: persönliche Anrede („Sehr geehrte/r
  Herr/Frau …" nur bei eindeutigem Geschlecht, sonst „Sehr geehrte/r …" oder
  „Guten Tag {{Name}}"). Sonst „Sehr geehrte Damen und Herren".
- KEINE Grußformel und KEINE Signatur schreiben — die Signatur wird automatisch
  angehängt. Beende den Text mit dem letzten inhaltlichen Satz.
- `body` als reiner Text mit \\n als Zeilenumbrüchen (kein HTML)."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Prägnante Betreffzeile, max. 80 Zeichen."},
        "body": {"type": "string", "description": "Der Mailtext inkl. Anrede, OHNE Grußformel/Signatur, \\n als Umbruch."},
        "product": {"type": "string", "description": "Das empfohlene Produkt (kurz), z. B. „Externer DSB“."},
    },
    "required": ["subject", "body"],
}


def build_lead_context(lead) -> str:
    """Lead-Felder → kompakter Kontextblock für den Prompt. Nur vorhandene Felder;
    keine erfundenen Werte. Reine Funktion (nimmt ein Objekt mit den Attributen)."""
    def val(x):
        return str(x).strip() if x not in (None, "") else None

    fields = [
        ("Firma", val(getattr(lead, "company", None))),
        ("Ansprechpartner", val(getattr(lead, "contact_name", None))),
        ("Funktion", val(getattr(lead, "role", None))),
        ("Geschäftsführung/Entscheider", val(getattr(lead, "decision_maker", None))),
        ("Target (Verkaufs-Winkel/Pain)", val(getattr(lead, "target", None))),
        ("Mitarbeiterzahl", val(getattr(lead, "employee_count", None))),
        ("Website", val(getattr(lead, "website", None))),
    ]
    tags = getattr(lead, "tags", None)
    if tags:
        fields.append(("Branche/Tags", ", ".join(str(t) for t in tags)))
    notes = val(getattr(lead, "notes", None))
    if notes:
        fields.append(("Notizen", notes[:600]))

    lines = [f"- {k}: {v}" for k, v in fields if v]
    return "\n".join(lines) if lines else "- (keine strukturierten Angaben)"


async def draft_lead_email(ai, model: str, lead, usage: Usage) -> dict:
    """Erzeugt {subject, body, product?} für den Lead. `usage` wird für die
    Kostenabrechnung befüllt (wie bei der KI-Lead-Suche)."""
    context = build_lead_context(lead)
    user = (
        "Schreibe die Erstansprache-Mail für diesen Lead. Empfiehl genau EIN "
        "Produkt, das am besten zum Target passt.\n\nLead-Infos:\n" + context
    )
    # max_tokens ist ein CAP, kein Verbrauch — man zahlt nur real erzeugte Tokens.
    # Grosszuegig, damit ein ~150-Woerter-Text (Deutsch = tokenreich) + Betreff +
    # Produkt nie mitten in der Tool-JSON abgeschnitten wird (sonst kaeme `body`
    # leer zurueck = nur Signatur). Gespart wird ueber den Draft-Cache, nicht hier.
    result = await _structured(
        ai, model, _SYSTEM, user,
        tool_name="draft_email", schema=_SCHEMA, usage=usage, max_tokens=1200,
    )
    # Defensive: leerer Text (z. B. abgeschnittene Tool-JSON) darf NICHT als
    # reiner Signatur-Block durchgehen — lieber klarer Fehler + Retry.
    body = str(result.get("body", "")).strip()
    if not body:
        raise ValueError("KI lieferte keinen Mailtext (nur leerer Body).")
    if SIGNATURE not in body:
        body = f"{body}\n\n{SIGNATURE}"
    return {
        "subject": str(result.get("subject", "")).strip(),
        "body": body,
        "product": str(result.get("product", "")).strip() or None,
    }
