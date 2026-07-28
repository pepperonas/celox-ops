"""Lead aus einem Chat-Verlauf aktualisieren (Text und/oder Screenshots).

Die KI **schlägt vor**, der Mensch entscheidet. Dieses Modul enthält den Prompt,
das Ausgabeschema und — wichtiger — die **Durchsetzung** der Regeln. Ein Prompt
ist eine Bitte; was hier steht, ist eine Prüfung.

Die vier Regeln, die im Code stehen und nicht nur im Prompt:

1. **Nichts erfinden.** Jeder Stammdatenvorschlag MUSS ein wörtliches Belegzitat
   mitbringen. Fehlt es, wird der Vorschlag verworfen und als „nicht belegt"
   ausgewiesen — keine geschätzte Firmengröße, keine gefolgerte Rolle.
2. **Keine Punkte für importierte Historie.** Erledigte Aktivitäten werden direkt
   mit `status=done` und historischem `completed_at` angelegt, nie über
   `POST /activities/{id}/complete`. Damit läuft weder `register_completion`
   (Punkte/Streak) noch der Next-Action-Zwang an — genau wie beim LinkedIn-Import.
3. **Nachvollziehbar.** Jede erzeugte Aktivität trägt den Präfix
   `[KI aus Chat, <Datum> · <Fingerprint>]` plus gekappten Originalauszug.
4. **Idempotent.** Der Fingerprint im Präfix ist der Dedup-Schlüssel: derselbe
   Verlauf zweimal eingespielt erzeugt keine Dubletten.

Alles außer `analyze_chat` ist rein und damit netz-/DB-frei testbar.
"""
import hashlib
import re
from datetime import date, datetime, timezone

from app.models.rainmaker_activity import RainmakerActivityType
from app.models.rainmaker_lead import RainmakerLeadStatus
from app.services.taxonomy import canonicalize

# Bei JEDER inhaltlichen Prompt-/Schema-Änderung hochzählen: fließt in den
# Material-Hash und verwirft damit gespeicherte Vorschläge (sonst käme ein
# Vorschlag nach alten Regeln zurück).
PROMPT_VERSION = "1"

# Grenzen für das Material. Der Client verkleinert Bilder schon im Browser;
# das hier ist die harte Schranke.
MAX_IMAGES = 6
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 15 * 1024 * 1024
MAX_TEXT_CHARS = 60_000
ALLOWED_IMAGE_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# Auszug im Notiztext — lang genug zum Wiedererkennen, kurz genug fürs Auge.
EXCERPT_CHARS = 400
# Der Fingerprint deckt nur den Anfang des Auszugs ab, damit kleine Abweichungen
# am Ende (Modell formuliert die Kappung anders) die Idempotenz nicht sprengen.
FINGERPRINT_SOURCE_CHARS = 120

_FIELD_LABELS = {
    "contact_name": "Ansprechpartner",
    "role": "Funktion",
    "decision_maker": "Entscheider",
    "employee_count": "Mitarbeiterzahl",
    "email": "E-Mail",
    "phone": "Telefon",
    "website": "Website",
    "target": "Target",
    "tags": "Tags",
    "status": "Status",
}
# Felder, die ohne Belegzitat NIE gesetzt werden dürfen (alle — die Liste ist
# identisch, aber explizit, damit ein neues Feld bewusst eingetragen wird).
EVIDENCE_REQUIRED = set(_FIELD_LABELS)

_DIRECTIONS = {"eingehend", "ausgehend", "intern"}


# --------------------------------------------------------------------------- #
#  Hashes / Fingerprints
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def material_hash(text: str, image_digests: list[str], lead, model: str,
                  prompt_version: str = PROMPT_VERSION) -> str:
    """Stabiler Hash über Material + relevanten Lead-Stand + Modell + Prompt.

    Rein. Identisches Material am unveränderten Lead ⇒ derselbe Hash ⇒ derselbe
    gespeicherte Vorschlag (kein zweiter KI-Call, gleiche Fingerprints).
    """
    def s(x):
        return "" if x in (None, "") else str(x).strip()

    parts = [
        f"p{prompt_version}", model, _norm(text),
        "|".join(sorted(image_digests)),
        s(getattr(lead, "company", None)), s(getattr(lead, "contact_name", None)),
        s(getattr(lead, "role", None)), s(getattr(lead, "decision_maker", None)),
        s(getattr(lead, "employee_count", None)), s(getattr(lead, "email", None)),
        s(getattr(lead, "phone", None)), s(getattr(lead, "website", None)),
        s(getattr(lead, "target", None)), s(getattr(lead, "status", None)),
        "|".join(str(t) for t in (getattr(lead, "tags", None) or [])),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def activity_fingerprint(activity_type: str, day: str, excerpt: str) -> str:
    """Kurzer Dedup-Schlüssel aus Typ + Datum + Anfang des Auszugs. Rein."""
    base = f"{activity_type}|{day}|{_norm(excerpt)[:FINGERPRINT_SOURCE_CHARS]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:6]


def activity_note(day: str, direction: str | None, excerpt: str, fingerprint: str) -> str:
    """Notiztext einer erzeugten Aktivität — Herkunft vorne, Auszug dahinter.

    Richtung steckt im Text, weil das Modell kein `direction`-Feld hat (gleiches
    Muster wie beim LinkedIn-Import).
    """
    head = f"[KI aus Chat, {day} · {fingerprint}]"
    if direction:
        head += f" {direction}:"
    return f"{head} {(excerpt or '').strip()[:EXCERPT_CHARS]}".strip()


def existing_fingerprints(activities) -> set[str]:
    """Fingerprints, die am Lead schon vorhanden sind (aus den Notiztexten)."""
    found: set[str] = set()
    for act in activities or []:
        for match in re.finditer(r"\[KI aus Chat, [^\]]*·\s*([0-9a-f]{6})\]",
                                 getattr(act, "notes", "") or ""):
            found.add(match.group(1))
    return found


# --------------------------------------------------------------------------- #
#  Normalisierung der KI-Ausgabe
# --------------------------------------------------------------------------- #
def _clean_day(value) -> str | None:
    """ISO-Datum (YYYY-MM-DD) aus der Modellausgabe, sonst None."""
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _clean_type(value) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in {t.value for t in RainmakerActivityType} else None


def _clean_int(value) -> int | None:
    """Nur echte Zahlen — „ca. 50-100 Mitarbeiter" ist keine belegte Zahl."""
    match = re.fullmatch(r"\s*(\d{1,7})\s*", str(value or ""))
    if match:
        return int(match.group(1))
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _has_evidence(item: dict) -> bool:
    return len(str(item.get("evidence") or "").strip()) >= 8


def _ignored(field: str, reason: str) -> dict:
    return {"field": field, "label": _FIELD_LABELS.get(field, field), "reason": reason}


# --------------------------------------------------------------------------- #
#  Diff-Aufbau — das Herz
# --------------------------------------------------------------------------- #
def build_proposal(ai_output: dict, lead, existing_activities=None,
                   today: date | None = None) -> dict:
    """KI-Ausgabe → Vorschlagsliste für den Dialog (rein, testbar).

    Jeder Eintrag hat einen stabilen `key` (den `apply` später auswählt), ein
    `preselected`-Flag und alles, was der Dialog zum Erklären braucht. Was
    verworfen wurde, steht mit Begründung in `ignored` — Stillschweigen wäre
    hier das Schlimmste.
    """
    today = today or datetime.now(timezone.utc).date()
    known = existing_fingerprints(existing_activities)
    seen: set[str] = set()

    notes: list[dict] = []
    activities: list[dict] = []
    fields: list[dict] = []
    next_action: dict | None = None
    ignored: list[dict] = []

    # ---- Notizzeilen: anfügen, nie ersetzen -------------------------------
    for i, line in enumerate(ai_output.get("notes_lines") or []):
        text = str(line or "").strip()
        if not text:
            continue
        notes.append({"key": f"note:{i}", "text": text[:500], "preselected": True})

    # ---- Erledigte Aktivitäten aus dem Verlauf ----------------------------
    for i, raw in enumerate(ai_output.get("activities") or []):
        act_type = _clean_type(raw.get("type"))
        day = _clean_day(raw.get("occurred_on"))
        excerpt = str(raw.get("excerpt") or "").strip()
        if not act_type:
            ignored.append(_ignored("activity", f"unbekannter Aktivitätstyp „{raw.get('type')}“"))
            continue
        if not day:
            ignored.append(_ignored("activity", "kein belegtes Datum im Material"))
            continue
        if day > today.isoformat():
            ignored.append(_ignored("activity", f"Datum {day} liegt in der Zukunft"))
            continue
        if not excerpt:
            ignored.append(_ignored("activity", "kein Originalauszug"))
            continue

        direction = str(raw.get("direction") or "").strip().lower()
        direction = direction if direction in _DIRECTIONS else None
        fp = activity_fingerprint(act_type, day, excerpt)
        duplicate = fp in known or fp in seen
        seen.add(fp)
        activities.append({
            "key": f"act:{i}",
            "type": act_type,
            "day": day,
            "direction": direction,
            "excerpt": excerpt[:EXCERPT_CHARS],
            "fingerprint": fp,
            "note": activity_note(day, direction, excerpt, fp),
            "duplicate": duplicate,
            # Duplikate NICHT vorauswählen — derselbe Verlauf zweimal
            # eingeworfen soll nichts verdoppeln.
            "preselected": not duplicate,
        })

    # ---- Höchstens EINE nächste geplante Aktion ---------------------------
    raw_next = ai_output.get("next_action") or None
    if isinstance(raw_next, dict):
        n_type = _clean_type(raw_next.get("type"))
        n_due = _clean_day(raw_next.get("due_date"))
        if n_type and n_due:
            next_action = {
                "key": "next", "type": n_type, "due_date": n_due,
                "reason": str(raw_next.get("reason") or "").strip()[:300],
                "preselected": True,
            }
        elif raw_next:
            ignored.append(_ignored("next_action", "Typ oder Datum fehlten"))

    # ---- Stammdaten: nur mit Belegzitat ----------------------------------
    for raw in ai_output.get("fields") or []:
        name = str(raw.get("field") or "").strip()
        if name not in _FIELD_LABELS:
            if name:
                ignored.append(_ignored(name, "Feld ist für den Chat-Import nicht freigegeben"))
            continue
        if name in EVIDENCE_REQUIRED and not _has_evidence(raw):
            ignored.append(_ignored(name, "kein wörtlicher Beleg im Material — nicht übernommen"))
            continue

        old = getattr(lead, name, None)
        new = _coerce_field(name, raw.get("value"))
        if new is None:
            ignored.append(_ignored(name, "Wert war leer oder unbrauchbar"))
            continue
        if _same(name, old, new):
            ignored.append(_ignored(name, "Wert steht schon so am Lead"))
            continue

        fields.append({
            "key": f"field:{name}",
            "field": name,
            "label": _FIELD_LABELS[name],
            "old": _display(old),
            "new": _display(new),
            "value": new,
            "evidence": str(raw.get("evidence") or "").strip()[:300],
            # Status ist eine fachliche Entscheidung (won/lost sind schwer) —
            # vorschlagen ja, vorauswählen nein.
            "preselected": name != "status",
        })

    return {
        "notes": notes,
        "activities": activities,
        "next_action": next_action,
        "fields": fields,
        "ignored": ignored,
        "summary": str(ai_output.get("summary") or "").strip()[:500],
    }


def _coerce_field(name: str, value):
    """Rohwert der KI → gespeicherter Typ, oder None wenn unbrauchbar."""
    if name == "employee_count":
        return _clean_int(value)
    if name == "tags":
        raw = value if isinstance(value, list) else [value]
        out: list[str] = []
        for tag in raw:
            text = canonicalize("tag", str(tag or "").strip())
            if text and text not in out:
                out.append(text[:60])
        return out or None
    if name == "status":
        text = str(value or "").strip().lower()
        return text if text in {s.value for s in RainmakerLeadStatus} else None
    text = str(value or "").strip()
    if not text:
        return None
    if name in ("role", "target"):
        text = canonicalize("target" if name == "target" else "role", text)
    return text[:255]


def _same(name: str, old, new) -> bool:
    if name == "tags":
        return sorted(str(t) for t in (old or [])) == sorted(str(t) for t in (new or []))
    if name == "status":
        return str(getattr(old, "value", old) or "") == str(new)
    if name == "employee_count":
        return old is not None and int(old) == int(new)
    return _norm(str(old or "")) == _norm(str(new or ""))


def _display(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—"
    return str(getattr(value, "value", value))


# --------------------------------------------------------------------------- #
#  Auswahl anwenden (rein: liefert nur, WAS zu tun ist)
# --------------------------------------------------------------------------- #
def select_items(proposal: dict, keys: list[str]) -> dict:
    """Vorschlag + Auswahl-Keys → die tatsächlich zu schreibenden Teile.

    Bewusst rein: der Router setzt danach um, entscheidet aber nichts mehr.
    Unbekannte Keys werden ignoriert (ein alter Dialog kann nichts erzwingen).
    """
    wanted = set(keys or [])
    picked_activities = [a for a in proposal.get("activities", []) if a["key"] in wanted]
    return {
        "note_lines": [n["text"] for n in proposal.get("notes", []) if n["key"] in wanted],
        "activities": picked_activities,
        "next_action": (proposal.get("next_action")
                        if proposal.get("next_action") and proposal["next_action"]["key"] in wanted
                        else None),
        "fields": [f for f in proposal.get("fields", []) if f["key"] in wanted],
    }


def notes_block(lines: list[str], day: str) -> str:
    """Der Textblock, der an `lead.notes` ANGEFÜGT wird (nie ersetzt)."""
    body = "\n".join(f"- {line}" for line in lines if line)
    return f"— aus Chat, {day} —\n{body}" if body else ""


def append_notes(existing: str | None, block: str) -> str:
    """Bestehende Notizen + neuer Block. Handgepflegter Text bleibt vorne."""
    if not block:
        return existing or ""
    base = (existing or "").rstrip()
    return f"{base}\n\n{block}" if base else block


# --------------------------------------------------------------------------- #
#  KI-Aufruf
# --------------------------------------------------------------------------- #
_SYSTEM = """Du wertest Gesprächsmaterial zu EINEM Geschäftskontakt aus (eingefügter
Chat-/E-Mail-Verlauf und/oder Screenshots davon) und schlägst Aktualisierungen für
einen CRM-Datensatz vor.

OBERSTE REGEL: Du erfindest NICHTS. Du extrahierst nur, was im Material wörtlich
steht oder sichtbar ist. Du schließt NICHT aus Indizien:
- keine geschätzte Mitarbeiterzahl („mittelständisch" ist keine Zahl)
- keine gefolgerte Funktion („klingt wie ein Chef" ist kein Beleg)
- keine erratenen Kontaktdaten
Wenn etwas unklar ist, lässt du es weg. Weglassen ist richtig, Raten ist falsch.

Zu JEDEM Stammdatenvorschlag lieferst du in `evidence` ein wörtliches Zitat aus
dem Material (mind. 8 Zeichen), das den Wert belegt. Ohne Zitat wird der
Vorschlag verworfen — dann lass ihn gleich weg.

AKTIVITÄTEN: Erfasse die stattgefundenen Kontakte als einzelne Einträge mit
- `type`: call | email | message | visit | follow_up | note
- `occurred_on`: das Datum aus dem Material (YYYY-MM-DD). Steht dort kein Datum,
  lass den Eintrag weg — rate keines.
- `direction`: eingehend | ausgehend | intern
- `excerpt`: kurzer Originalauszug (max. 400 Zeichen, wörtlich, nicht umformuliert)
Fasse einen Gesprächsverlauf zu sinnvollen Einheiten zusammen, nicht jede Zeile
einzeln. Keine Einträge in der Zukunft.

NÄCHSTE AKTION: höchstens EINE, nur wenn im Material eine konkrete Zusage oder
Verabredung steht („ich melde mich Montag", „Angebot bis Freitag"). Sonst null.

NOTIZEN: kurze Stichpunkte mit dem, was für die Akquise zählt (Bedarf, Einwände,
Budget, Entscheidungswege, Fristen). Keine Wiederholung des ganzen Verlaufs.

STATUS: nur vorschlagen, wenn das Material es klar hergibt. Bei „won"/„lost" sei
besonders zurückhaltend — das entscheidet der Mensch.

Sprache: Deutsch, Sie-Form in Zitaten wie im Original."""


def build_user_content(text: str, images: list[dict], lead) -> list[dict]:
    """Message-Content für den Vision-Call: Bilder zuerst, dann Text.

    `images` sind `{"media_type": ..., "b64": ...}`. Bilder vor Text ist die von
    Anthropic empfohlene Reihenfolge für Bild+Frage-Aufgaben.
    """
    blocks: list[dict] = []
    for img in images or []:
        blocks.append({"type": "image", "source": {
            "type": "base64", "media_type": img["media_type"], "data": img["b64"]}})

    context = [f"Firma: {getattr(lead, 'company', '') or '—'}"]
    for attr, label in (("contact_name", "Ansprechpartner"), ("role", "Funktion"),
                        ("decision_maker", "Entscheider"), ("target", "Target"),
                        ("email", "E-Mail"), ("phone", "Telefon"),
                        ("employee_count", "Mitarbeiterzahl")):
        value = getattr(lead, attr, None)
        if value:
            context.append(f"{label}: {value}")
    status = getattr(lead, "status", None)
    if status is not None:
        context.append(f"Status: {getattr(status, 'value', status)}")

    prompt = ["Aktueller Datenstand des Leads (nur zum Abgleich — nicht als Beleg):",
              "\n".join(context)]
    if (text or "").strip():
        prompt += ["", "Material (eingefügter Verlauf):", (text or "").strip()[:MAX_TEXT_CHARS]]
    if images:
        prompt += ["", f"Dazu {len(images)} Screenshot(s) desselben Verlaufs (siehe Bilder)."]
    prompt += ["", "Werte das Material aus und gib die Vorschläge strukturiert zurück."]
    blocks.append({"type": "text", "text": "\n".join(prompt)})
    return blocks


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "Ein Satz: worum ging es im Verlauf?"},
        "notes_lines": {
            "type": "array", "items": {"type": "string"},
            "description": "Kurze Stichpunkte für die Lead-Notizen (Bedarf, Einwände, Fristen).",
        },
        "activities": {
            "type": "array",
            "description": "Stattgefundene Kontakte, je mit Datum aus dem Material.",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": [t.value for t in RainmakerActivityType]},
                    "occurred_on": {"type": "string", "description": "YYYY-MM-DD aus dem Material."},
                    "direction": {"type": "string", "enum": sorted(_DIRECTIONS)},
                    "excerpt": {"type": "string", "description": "Wörtlicher Auszug, max. 400 Zeichen."},
                },
                "required": ["type", "occurred_on", "excerpt"],
            },
        },
        "next_action": {
            "type": ["object", "null"],
            "description": "Höchstens eine konkret verabredete nächste Aktion, sonst null.",
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in RainmakerActivityType]},
                "due_date": {"type": "string", "description": "YYYY-MM-DD."},
                "reason": {"type": "string", "description": "Worauf im Material sich das stützt."},
            },
        },
        "fields": {
            "type": "array",
            "description": "Stammdaten, die das Material BELEGT. Ohne Zitat weglassen.",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": sorted(_FIELD_LABELS)},
                    "value": {"description": "Neuer Wert (Zahl bei employee_count, Liste bei tags)."},
                    "evidence": {"type": "string", "description": "Wörtliches Zitat als Beleg."},
                },
                "required": ["field", "value", "evidence"],
            },
        },
    },
    "required": ["notes_lines", "activities", "fields"],
}


async def analyze_chat(ai, model: str, *, text: str, images: list[dict], lead, usage) -> dict:
    """Ein Claude-Call (Vision + Text) mit erzwungener Struktur.

    Nutzt `_structured` aus `ai_lead_agent` — ein KI-Stack, ein Kostenzähler.
    """
    from app.services.ai_lead_agent import _structured

    return await _structured(
        ai, model, _SYSTEM, build_user_content(text, images, lead),
        "lead_update", PROPOSAL_SCHEMA, usage, max_tokens=3000,
    )
