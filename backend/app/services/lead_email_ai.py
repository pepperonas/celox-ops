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
PROMPT_VERSION = "4"

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

_SYSTEM = f"""Du bist {_SENDER} und schreibst eine kurze, seriöse deutsche Erstansprache
(Kaltakquise per E-Mail) an einen potenziellen Kunden.

Absender-Profil & Portfolio (wähle das EINE Produkt, das am besten zum „Target"
und zur Branche des Empfängers passt):
- IT-Sicherheit: Audits, ISMS-Aufbau/-Betreuung nach ISO 27001, IT-Grundschutz,
  NIS2, Security-Awareness. (Kredential: ISO 27001, BSI IT-Grundschutz.)
- Datenschutz: externer Datenschutzbeauftragter (IHK), DSGVO-Umsetzung,
  Datenschutz-Managementsystem (DSMS, datenschutz.celox.io).
- bcsbook — unser eigenes Produkt: automatische, aktivitätsbasierte
  Zeiterfassung, die direkt in ein VORHANDENES Projektron BCS bucht (es ersetzt
  BCS nicht und führt BCS nicht ein, sondern automatisiert das lästige Erfassen).
  So funktioniert es: bcsbook erkennt im Hintergrund, woran jemand tatsächlich
  gearbeitet hat (Git-Commits, IDE-/Editor-Aktivität, KI-CLI-Sitzungen,
  Azure-DevOps-Tickets — und für Nicht-Entwickler wie PMs/Beratende über eine
  Anwesenheits-Erkennung), bündelt das in 15-Minuten-Blöcke je Projekt und bucht
  sie nach kurzer Bestätigung automatisch in BCS. Aus 5–10 händischen
  BCS-Einträgen pro Tag wird „F5 → prüfen → buchen".
  Nutzen für den Entscheider (nur nennen, was passt):
  * Spart jedem Mitarbeitenden ~15–20 Min/Tag Buchungsaufwand — die gesetzlich
    verpflichtende Zeiterfassung (BAG-Urteil) wird reibungslos statt lästig.
  * Höhere Datenqualität: Buchungen beruhen auf der realen Tagesaktivität statt
    auf Abend-Erinnerung/Schätzung → sauberere Projektabrechnung.
  * Jede Buchung wird gegen BCS verifiziert und bei Bedarf automatisch einmal
    wiederholt — nichts geht verloren.
  * Datenschutz & Kontrolle: läuft rein lokal/on-premise (nur 127.0.0.1, keine
    Cloud), nichts wird ohne Bestätigung gebucht, Einträge sind jederzeit
    editier- und löschbar — kein Überwachungsgefühl, die Mitarbeitenden behalten
    die Hand drauf.
- Individualsoftware & Prozessautomatisierung.

Regeln:
- Führe mit dem NUTZEN/Pain aus dem „Target", nicht mit einer Selbstvorstellung.
- Genau EIN passendes Produkt empfehlen, kein Bauchladen.
- Wenn das „Target"/die Branche mit Zeiterfassung, Stundenzetteln, BCS oder
  Projektabrechnung zu tun hat: empfiehl bcsbook und mache den Nutzen GREIFBAR.
  Führe mit der Transformation (aus 5–10 Handbuchungen/Tag wird kurz bestätigen)
  und dem konkreten Gewinn (Zeit gespart, höhere Abrechnungsqualität,
  on-premise/Datenschutz, Mitarbeitende behalten die Kontrolle). Ziel: Neugier
  und ein GUTES GEFÜHL wecken (Entlastung — nicht noch ein Tool, das Arbeit
  macht). Wenn die Mitarbeiterzahl bekannt ist, rechne den Nutzen kurz darauf
  hoch (z. B. „bei 85 Mitarbeitenden…"); sonst NICHT erfinden. KEINE generische
  „Einführung/Beratung/Anpassung von BCS" — bcsbook ist ein fertiges Produkt, das
  die BCS-Zeiterfassung automatisiert. Keine erfundenen Zahlen darüber hinaus.
- Konkreter, unaufdringlicher Call-to-Action (kurzes Gespräch / 15-Minuten-Call).
- Max. ~150 Wörter Fließtext, Sie-Form, keine Übertreibung, keine erfundenen
  Fakten über den Empfänger (nutze nur die gegebenen Infos). Konkret und
  bildhaft schlägt lang und vage — lieber ein greifbarer Nutzen als drei Floskeln.
- Wenn ein Ansprechpartner bekannt ist: persönliche Anrede („Sehr geehrte/r
  Herr/Frau …" nur wenn das Geschlecht eindeutig ist, sonst „Sehr geehrte/r …"
  oder „Guten Tag {{Name}}"). Sonst „Sehr geehrte Damen und Herren".
- KEINE Grußformel und KEINE Signatur schreiben — die Signatur wird
  automatisch angehängt. Beende den Text mit dem letzten inhaltlichen Satz
  (z. B. der Frage nach einem Termin).
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
