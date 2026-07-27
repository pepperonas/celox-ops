"""Kontoauszug einlesen und Zahlungen Rechnungen zuordnen.

Zahlungen wurden bisher von Hand gebucht. Hier entsteht der Vorschlag: Auszug
einlesen → Gutschriften den offenen Rechnungen zuordnen → **Vorschlagsliste**,
die der Nutzer bestätigt. Es wird **nichts automatisch gebucht** — eine falsch
zugeordnete Zahlung wäre teurer als ein Klick.

Bewusst **ohne** FinTS/Bank-API: der Datei-Import (camt.053-XML oder CSV-Export)
braucht keine Bankzugangsdaten und ist reine, gut testbare Parser-Logik.

Alles in diesem Modul ist rein — kein Netz, keine DB.

Unterstützt:
- **camt.052/053/054** (ISO 20022, alle deutschen Banken liefern das)
- **CSV**-Exporte mit deutschen oder englischen Spaltenköpfen (Sparkasse, DKB,
  Volksbank, Commerzbank, N26 … über Spalten-Aliase statt pro-Bank-Sonderfällen)
"""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

# --------------------------------------------------------------------------- #
#  Datenhaltung
# --------------------------------------------------------------------------- #
CONFIDENCE_EXACT = "exact"        # Rechnungsnummer + Betrag passen
CONFIDENCE_NUMBER = "number"      # Rechnungsnummer passt, Betrag weicht ab
CONFIDENCE_AMOUNT = "amount"      # keine Nummer, aber genau eine Rechnung mit dem Betrag


def tx(booking_date, amount, purpose, counterparty=None, reference=None,
       currency="EUR", credit=True) -> dict:
    """Eine normalisierte Buchung (Rückgabetyp der Parser)."""
    return {
        "booking_date": booking_date.isoformat() if hasattr(booking_date, "isoformat") else booking_date,
        "amount": str(amount),
        "currency": currency,
        "purpose": (purpose or "").strip(),
        "counterparty": (counterparty or "").strip() or None,
        "reference": (reference or "").strip() or None,
        "credit": bool(credit),
    }


# --------------------------------------------------------------------------- #
#  Zahlen und Datumsangaben
# --------------------------------------------------------------------------- #
def parse_amount(raw) -> Decimal | None:
    """„1.234,56" / „1234.56" / „-45,00 EUR" → Decimal. None bei Unlesbarem.

    Deutsche und englische Schreibweise werden unterschieden, indem geprüft
    wird, welches Zeichen zuletzt steht (das ist das Dezimaltrennzeichen).
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float, Decimal)):
        return Decimal(str(raw))
    text = re.sub(r"[^\d,.\-+]", "", str(raw)).strip()
    if not text or text in ("-", "+"):
        return None
    last_comma, last_dot = text.rfind(","), text.rfind(".")
    if last_comma > last_dot:                     # deutsch: 1.234,56
        text = text.replace(".", "").replace(",", ".")
    else:                                         # englisch: 1,234.56
        text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")


def parse_date(raw) -> date | None:
    if raw is None or isinstance(raw, date):
        return raw
    text = str(raw).strip()[:10]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
#  camt (ISO 20022)
# --------------------------------------------------------------------------- #
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(node, *names) -> str | None:
    """Ersten Nachfahren mit einem dieser lokalen Tag-Namen als Text liefern
    (Namensraum-unabhängig — die camt-Versionen unterscheiden sich darin)."""
    for child in node.iter():
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return None


# Hochgeladene Dateien sind nicht vertrauenswürdig. Der stdlib-XML-Parser löst
# keine EXTERNEN Entities auf (kein Dateizugriff/SSRF), ist aber anfällig für
# Entity-Expansion („billion laughs"): wenige Kilobyte blähen sich zu Gigabyte
# im Speicher auf. Beides braucht eine DOCTYPE-/ENTITY-Deklaration — die ein
# echter Bank-camt-Export nie enthält. Wir weisen sie deshalb vor dem Parsen ab
# (schließt die Angriffe ohne zusätzliche Abhängigkeit) und deckeln die Größe.
MAX_STATEMENT_BYTES = 10 * 1024 * 1024
_DOCTYPE_RE = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


def _reject_doctype(raw: bytes) -> None:
    if _DOCTYPE_RE.search(raw):
        raise ValueError(
            "Die XML-Datei enthält eine DOCTYPE-/ENTITY-Deklaration und wird aus "
            "Sicherheitsgründen abgewiesen. Bank-Exporte (camt.053) brauchen keine."
        )


def parse_camt(content: bytes | str) -> list[dict]:
    """camt.052/053/054 → Liste normalisierter Buchungen."""
    raw = content if isinstance(content, bytes) else content.encode()
    if len(raw) > MAX_STATEMENT_BYTES:
        raise ValueError("Die Datei ist zu groß (max. 10 MB).")
    _reject_doctype(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"Die XML-Datei ist nicht lesbar: {exc}") from exc

    entries = [n for n in root.iter() if _local(n.tag) == "Ntry"]
    if not entries:
        raise ValueError("Keine Buchungen (Ntry) gefunden — ist das eine camt-Datei?")

    out: list[dict] = []
    for entry in entries:
        amount_node = next((n for n in entry.iter() if _local(n.tag) == "Amt"), None)
        amount = parse_amount(amount_node.text if amount_node is not None else None)
        if amount is None:
            continue
        currency = (amount_node.get("Ccy") or "EUR") if amount_node is not None else "EUR"
        credit = (_find_text(entry, "CdtDbtInd") or "CRDT").upper() == "CRDT"

        booking = None
        for date_tag in ("BookgDt", "ValDt"):
            node = next((n for n in entry.iter() if _local(n.tag) == date_tag), None)
            if node is not None:
                booking = parse_date(_find_text(node, "Dt", "DtTm"))
                if booking:
                    break

        # Verwendungszweck: alle Ustrd-Zeilen zusammen (Banken splitten auf 140 Zeichen)
        purpose = " ".join(
            (n.text or "").strip() for n in entry.iter()
            if _local(n.tag) == "Ustrd" and (n.text or "").strip()
        )
        if not purpose:
            purpose = _find_text(entry, "AddtlNtryInf") or ""

        # Gegenpartei: bei Gutschrift der Zahlende (Dbtr), sonst der Empfänger
        party_tag = "Dbtr" if credit else "Cdtr"
        party = next((n for n in entry.iter() if _local(n.tag) == party_tag), None)
        counterparty = _find_text(party, "Nm") if party is not None else None

        out.append(tx(booking or date.today(), amount.copy_abs(), purpose,
                      counterparty=counterparty,
                      reference=_find_text(entry, "EndToEndId", "AcctSvcrRef"),
                      currency=currency, credit=credit))
    return out


# --------------------------------------------------------------------------- #
#  CSV
# --------------------------------------------------------------------------- #
# Spalten-Aliase statt Sonderbehandlung pro Bank (klein geschrieben, ohne Umlaute).
_COL_DATE = ("buchungstag", "buchungsdatum", "valuta", "valutadatum", "wertstellung",
             "datum", "date", "booking date", "bookingdate", "transaction date")
_COL_AMOUNT = ("betrag", "betrag (eur)", "betrag eur", "umsatz", "amount", "value")
_COL_PURPOSE = ("verwendungszweck", "buchungstext verwendungszweck", "beschreibung",
                "vorgang verwendungszweck", "verwendungszweck (zahlungsreferenz)",
                "payment reference", "reference", "description", "details")
_COL_PARTY = ("beguenstigter/zahlpflichtiger", "beguenstigter", "zahlungsempfaenger",
              "auftraggeber/empfaenger", "auftraggeber", "empfaenger", "name",
              "payer", "payee", "partner name", "counterparty")
_COL_TYPE = ("buchungstext", "umsatzart", "vorgang", "transaction type", "typ")


def _fold(text: str) -> str:
    out = (text or "").strip().lower().replace('"', "")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        out = out.replace(a, b)
    return re.sub(r"\s+", " ", out)


def resolve_columns(header: list[str]) -> dict:
    """Spaltenköpfe → Feldzuordnung. Unbekannte Exporte scheitern hier sichtbar
    statt still falsche Spalten zu lesen."""
    folded = [_fold(h) for h in header]

    def pick(aliases) -> int | None:
        for i, name in enumerate(folded):        # exakter Treffer zuerst
            if name in aliases:
                return i
        for i, name in enumerate(folded):        # sonst Teilstring
            if any(a in name for a in aliases):
                return i
        return None

    return {
        "date": pick(_COL_DATE),
        "amount": pick(_COL_AMOUNT),
        "purpose": pick(_COL_PURPOSE),
        "party": pick(_COL_PARTY),
        "type": pick(_COL_TYPE),
    }


def parse_csv(content: bytes | str) -> list[dict]:
    """Bank-CSV → Liste normalisierter Buchungen (Vorspann-Zeilen werden
    übersprungen, Trennzeichen automatisch erkannt)."""
    if isinstance(content, bytes) and len(content) > MAX_STATEMENT_BYTES:
        raise ValueError("Die Datei ist zu groß (max. 10 MB).")
    text = content.decode("utf-8-sig", errors="replace") if isinstance(content, bytes) else content
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        raise ValueError("Die Datei ist leer.")

    delimiter = ";" if lines[0].count(";") >= lines[0].count(",") else ","

    # Kopfzeile suchen: erste Zeile, in der Datum UND Betrag auflösbar sind
    # (viele Banken stellen Konto-/Zeitraumangaben davor).
    header_idx, cols = None, None
    for i, line in enumerate(lines[:15]):
        candidate = next(csv.reader([line], delimiter=delimiter), [])
        resolved = resolve_columns(candidate)
        if resolved["date"] is not None and resolved["amount"] is not None:
            header_idx, cols = i, resolved
            break
    if cols is None:
        raise ValueError(
            "Keine Kopfzeile mit Datum und Betrag erkannt. Erwartet werden Spalten "
            "wie 'Buchungstag' und 'Betrag' (oder ein camt.053-XML)."
        )

    out: list[dict] = []
    for row in csv.reader(io.StringIO("\n".join(lines[header_idx + 1:])), delimiter=delimiter):
        if not row or len(row) <= max(v for v in cols.values() if v is not None):
            continue
        amount = parse_amount(row[cols["amount"]])
        booking = parse_date(row[cols["date"]])
        if amount is None or booking is None or amount == 0:
            continue
        purpose_parts = [row[cols["purpose"]]] if cols["purpose"] is not None else []
        if cols["type"] is not None and row[cols["type"]].strip():
            purpose_parts.append(row[cols["type"]].strip())
        out.append(tx(
            booking, amount.copy_abs(), " ".join(p for p in purpose_parts if p),
            counterparty=row[cols["party"]] if cols["party"] is not None else None,
            credit=amount > 0,
        ))
    return out


def parse_statement(filename: str, content: bytes) -> list[dict]:
    """Format am **Inhalt** erkennen und einlesen.

    Die Dateiendung entscheidet bewusst NICHT: Bank-Exporte werden oft
    umbenannt, und eine als .xml gespeicherte CSV würde sonst am XML-Parser
    scheitern statt korrekt gelesen zu werden. `filename` bleibt nur für
    Fehlermeldungen erhalten.
    """
    head = content[:400].lstrip()
    if head.startswith(b"<"):
        return parse_camt(content)
    return parse_csv(content)


# --------------------------------------------------------------------------- #
#  Zuordnung
# --------------------------------------------------------------------------- #
def invoice_number_pattern(prefixes: list[str]) -> re.Pattern:
    """Regex für die eigenen Nummernkreise, tolerant gegenüber Trennzeichen —
    Kunden tippen „CO 2026 0001", „co-2026-0001" oder „CO20260001"."""
    alts = "|".join(re.escape(p) for p in sorted({p for p in prefixes if p}, key=len, reverse=True))
    return re.compile(rf"\b({alts})[\s\-_/.]*(\d{{4}})[\s\-_/.]*(\d{{1,6}})\b", re.IGNORECASE)


def extract_invoice_numbers(text: str, prefixes: list[str]) -> list[str]:
    """Alle erkannten Rechnungsnummern in kanonischer Form (PREFIX-JJJJ-NNNN)."""
    if not text or not prefixes:
        return []
    found: list[str] = []
    for prefix, year, seq in invoice_number_pattern(prefixes).findall(text):
        canonical = f"{prefix.upper()}-{year}-{seq.zfill(4)}"
        if canonical not in found:
            found.append(canonical)
    return found


def open_amount(invoice: dict) -> Decimal:
    return Decimal(str(invoice["total"])) - Decimal(str(invoice.get("amount_paid") or 0))


def match_transactions(transactions: list[dict], invoices: list[dict],
                       prefixes: list[str] | None = None) -> dict:
    """Buchungen → Zuordnungsvorschläge.

    `invoices` sind die **offenen** Rechnungen als dicts mit id/invoice_number/
    total/amount_paid/customer_name. Regeln, absteigend nach Verlässlichkeit:

    1. Rechnungsnummer im Verwendungszweck **und** Betrag = offener Rest → `exact`
    2. Rechnungsnummer erkannt, Betrag weicht ab → `number` (Teil-/Überzahlung)
    3. keine Nummer, aber **genau eine** offene Rechnung mit exakt dem Betrag → `amount`

    Mehrdeutigkeiten werden bewusst NICHT geraten, sondern bleiben unzugeordnet.
    Jede Rechnung erscheint höchstens einmal (der beste Treffer gewinnt), damit
    ein Bestätigen aller Vorschläge nie doppelt bucht.
    """
    prefixes = prefixes or sorted({
        str(inv["invoice_number"]).split("-")[0] for inv in invoices
        if inv.get("invoice_number") and "-" in str(inv["invoice_number"])
    })
    by_number = {str(inv["invoice_number"]).upper(): inv for inv in invoices}

    proposals: list[dict] = []
    unmatched: list[dict] = []
    ignored_debits = 0
    used_invoices: set = set()

    credits = [t for t in transactions if t.get("credit")]
    ignored_debits = len(transactions) - len(credits)

    # Runde 1: über die Rechnungsnummer (verlässlichster Schlüssel)
    rest: list[dict] = []
    for t in credits:
        haystack = " ".join(filter(None, [t.get("purpose"), t.get("reference")]))
        hit = next((by_number[n] for n in extract_invoice_numbers(haystack, prefixes)
                    if n in by_number), None)
        if hit is None:
            rest.append(t)
            continue
        if hit["id"] in used_invoices:
            unmatched.append({**t, "reason": f"Rechnung {hit['invoice_number']} in diesem "
                                            "Auszug bereits zugeordnet"})
            continue
        amount = Decimal(t["amount"])
        due = open_amount(hit)
        used_invoices.add(hit["id"])
        proposals.append(_proposal(
            t, hit, amount,
            CONFIDENCE_EXACT if amount == due else CONFIDENCE_NUMBER,
            "Rechnungsnummer und Betrag stimmen" if amount == due else
            (f"Rechnungsnummer erkannt, Betrag weicht ab (offen: {due} €)"),
        ))

    # Runde 2: eindeutiger Betrag
    for t in rest:
        amount = Decimal(t["amount"])
        candidates = [inv for inv in invoices
                      if inv["id"] not in used_invoices and open_amount(inv) == amount]
        if len(candidates) == 1:
            hit = candidates[0]
            used_invoices.add(hit["id"])
            proposals.append(_proposal(t, hit, amount, CONFIDENCE_AMOUNT,
                                       "Betrag passt genau zu einer offenen Rechnung"))
        elif len(candidates) > 1:
            unmatched.append({**t, "reason": f"{len(candidates)} offene Rechnungen mit "
                                            "diesem Betrag — nicht eindeutig"})
        else:
            unmatched.append({**t, "reason": "keine passende offene Rechnung"})

    return {
        "proposals": proposals,
        "unmatched": unmatched,
        "ignored_debits": ignored_debits,
        "transactions_total": len(transactions),
    }


def _proposal(t: dict, invoice: dict, amount: Decimal, confidence: str, reason: str) -> dict:
    return {
        "invoice_id": str(invoice["id"]),
        "invoice_number": invoice["invoice_number"],
        "customer_name": invoice.get("customer_name") or "",
        "invoice_total": str(invoice["total"]),
        "invoice_open": str(open_amount(invoice)),
        "amount": str(amount),
        "confidence": confidence,
        "reason": reason,
        "booking_date": t["booking_date"],
        "purpose": t["purpose"],
        "counterparty": t.get("counterparty"),
    }
