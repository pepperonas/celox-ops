"""DB-/netzfreie Tests für den Kontoauszug-Import und die Zahlungszuordnung."""
from decimal import Decimal

import pytest

from app.services.bank_import import (
    CONFIDENCE_AMOUNT,
    CONFIDENCE_EXACT,
    CONFIDENCE_NUMBER,
    extract_invoice_numbers,
    match_transactions,
    parse_amount,
    parse_camt,
    parse_csv,
    parse_date,
    parse_statement,
    resolve_columns,
)

# --- camt.053 (auf das Wesentliche gekürzt, Struktur wie bei echten Banken) --
_CAMT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
 <BkToCstmrStmt><Stmt>
  <Ntry>
   <Amt Ccy="EUR">1130.50</Amt><CdtDbtInd>CRDT</CdtDbtInd>
   <BookgDt><Dt>2026-07-15</Dt></BookgDt>
   <NtryDtls><TxDtls>
    <Refs><EndToEndId>NOTPROVIDED</EndToEndId></Refs>
    <RltdPties><Dbtr><Nm>Beispiel GmbH</Nm></Dbtr></RltdPties>
    <RmtInf><Ustrd>Rechnung CO-2026-0007</Ustrd><Ustrd> vielen Dank</Ustrd></RmtInf>
   </TxDtls></NtryDtls>
  </Ntry>
  <Ntry>
   <Amt Ccy="EUR">49.99</Amt><CdtDbtInd>DBIT</CdtDbtInd>
   <BookgDt><Dt>2026-07-16</Dt></BookgDt>
   <NtryDtls><TxDtls><RmtInf><Ustrd>Hosting</Ustrd></RmtInf></TxDtls></NtryDtls>
  </Ntry>
 </Stmt></BkToCstmrStmt>
</Document>"""

_CSV = """Buchungstag;Wertstellung;Buchungstext;Beguenstigter/Zahlpflichtiger;Verwendungszweck;Betrag
15.07.2026;15.07.2026;Gutschrift;Beispiel GmbH;Zahlung Re. CO 2026 0007;1.130,50
16.07.2026;16.07.2026;Lastschrift;Hoster AG;Serverkosten;-49,99
"""

_CSV_WITH_PREAMBLE = """Konto;DE02120300000000202051
Zeitraum;01.07.2026 - 31.07.2026

Datum;Name;Payment reference;Amount (EUR)
17.07.2026;Muster AG;CO-2026-0008 Teilzahlung;500.00
"""


def _inv(num, total, paid="0", iid=None, name="Beispiel GmbH"):
    return {"id": iid or num, "invoice_number": num, "customer_name": name,
            "total": Decimal(total), "amount_paid": Decimal(paid)}


# ---- Zahlen / Datum --------------------------------------------------------
def test_amount_handles_german_and_english_format():
    assert parse_amount("1.130,50") == Decimal("1130.50")
    assert parse_amount("1,130.50") == Decimal("1130.50")
    assert parse_amount("-49,99") == Decimal("-49.99")
    assert parse_amount("950.00 EUR") == Decimal("950.00")
    assert parse_amount("95") == Decimal("95")


def test_amount_rejects_garbage():
    assert parse_amount("") is None
    assert parse_amount("keine Zahl") is None
    assert parse_amount(None) is None


def test_date_formats():
    assert parse_date("15.07.2026").isoformat() == "2026-07-15"
    assert parse_date("2026-07-15").isoformat() == "2026-07-15"
    assert parse_date("Quatsch") is None


# ---- camt ------------------------------------------------------------------
def test_camt_parses_credit_and_debit():
    txs = parse_camt(_CAMT)
    assert len(txs) == 2
    credit = txs[0]
    assert credit["credit"] is True
    assert Decimal(credit["amount"]) == Decimal("1130.50")
    assert credit["booking_date"] == "2026-07-15"
    assert credit["counterparty"] == "Beispiel GmbH"
    assert txs[1]["credit"] is False


def test_camt_joins_split_purpose_lines():
    """Banken teilen den Verwendungszweck auf mehrere Ustrd-Felder auf."""
    assert "CO-2026-0007" in parse_camt(_CAMT)[0]["purpose"]
    assert "vielen Dank" in parse_camt(_CAMT)[0]["purpose"]


def test_camt_rejects_doctype_declaration():
    """Entity-Expansion („billion laughs") wird vor dem Parsen abgewiesen."""
    evil = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "aaaa">]>'
            '<Document><Ntry/></Document>')
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_camt(evil)


def test_camt_without_entries_is_an_error():
    with pytest.raises(ValueError, match="Ntry"):
        parse_camt('<?xml version="1.0"?><Document></Document>')


def test_broken_xml_is_an_error():
    with pytest.raises(ValueError, match="nicht lesbar"):
        parse_camt("<Document><Ntry>")


# ---- CSV -------------------------------------------------------------------
def test_csv_columns_resolved_by_alias():
    cols = resolve_columns(["Buchungstag", "Beguenstigter/Zahlpflichtiger",
                            "Verwendungszweck", "Betrag"])
    assert cols["date"] == 0 and cols["party"] == 1
    assert cols["purpose"] == 2 and cols["amount"] == 3


def test_csv_parses_and_signs_correctly():
    txs = parse_csv(_CSV)
    assert len(txs) == 2
    assert txs[0]["credit"] is True and Decimal(txs[0]["amount"]) == Decimal("1130.50")
    assert txs[1]["credit"] is False, "negativer Betrag = Belastung"
    assert Decimal(txs[1]["amount"]) == Decimal("49.99"), "Betrag wird absolut gespeichert"


def test_csv_skips_preamble_and_reads_english_headers():
    txs = parse_csv(_CSV_WITH_PREAMBLE)
    assert len(txs) == 1
    assert txs[0]["counterparty"] == "Muster AG"
    assert Decimal(txs[0]["amount"]) == Decimal("500.00")


def test_csv_without_recognizable_header_fails_loudly():
    with pytest.raises(ValueError, match="Kopfzeile"):
        parse_csv("Spalte A;Spalte B\n1;2\n")


def test_statement_detects_format_by_content_not_extension():
    assert len(parse_statement("auszug.txt", _CAMT.encode())) == 2
    assert len(parse_statement("auszug.xml", _CSV.encode())) == 2


# ---- Rechnungsnummern erkennen --------------------------------------------
def test_invoice_numbers_tolerate_separators():
    for text in ("CO-2026-0007", "co 2026 0007", "Re. CO/2026/0007", "CO_2026_0007"):
        assert extract_invoice_numbers(text, ["CO"]) == ["CO-2026-0007"], text


def test_invoice_numbers_pad_short_sequences():
    assert extract_invoice_numbers("CO-2026-7", ["CO"]) == ["CO-2026-0007"]


def test_invoice_numbers_ignore_foreign_prefixes():
    assert extract_invoice_numbers("XY-2026-0007", ["CO"]) == []
    assert extract_invoice_numbers("CO-2026-0007", []) == []


def test_multiple_numbers_are_all_found_once():
    text = "Sammelzahlung CO-2026-0001, CO-2026-0002 und nochmal CO-2026-0001"
    assert extract_invoice_numbers(text, ["CO"]) == ["CO-2026-0001", "CO-2026-0002"]


# ---- Zuordnung -------------------------------------------------------------
def test_number_and_amount_match_is_exact():
    res = match_transactions(parse_camt(_CAMT), [_inv("CO-2026-0007", "1130.50")])
    assert len(res["proposals"]) == 1
    p = res["proposals"][0]
    assert p["confidence"] == CONFIDENCE_EXACT
    assert p["invoice_number"] == "CO-2026-0007"
    assert res["ignored_debits"] == 1, "Belastungen werden nicht zugeordnet"


def test_number_match_with_deviating_amount_is_flagged():
    res = match_transactions(parse_camt(_CAMT), [_inv("CO-2026-0007", "2000.00")])
    p = res["proposals"][0]
    assert p["confidence"] == CONFIDENCE_NUMBER
    assert "weicht ab" in p["reason"]
    assert p["invoice_open"] == "2000.00"


def test_partial_payment_uses_remaining_open_amount():
    res = match_transactions(parse_camt(_CAMT),
                             [_inv("CO-2026-0007", "2261.00", paid="1130.50")])
    assert res["proposals"][0]["confidence"] == CONFIDENCE_EXACT


def test_unique_amount_matches_without_number():
    txs = [{"booking_date": "2026-07-20", "amount": "476.00", "purpose": "Ueberweisung",
            "credit": True, "counterparty": "Kunde", "reference": None}]
    res = match_transactions(txs, [_inv("CO-2026-0011", "476.00"),
                                   _inv("CO-2026-0012", "999.00")])
    assert res["proposals"][0]["confidence"] == CONFIDENCE_AMOUNT


def test_ambiguous_amount_is_not_guessed():
    txs = [{"booking_date": "2026-07-20", "amount": "476.00", "purpose": "",
            "credit": True, "counterparty": None, "reference": None}]
    res = match_transactions(txs, [_inv("CO-2026-0011", "476.00", iid="a"),
                                   _inv("CO-2026-0012", "476.00", iid="b")])
    assert res["proposals"] == []
    assert "nicht eindeutig" in res["unmatched"][0]["reason"]


def test_each_invoice_is_proposed_at_most_once():
    """Zwei Buchungen mit derselben Rechnungsnummer dürfen nicht doppelt buchen."""
    txs = [
        {"booking_date": "2026-07-20", "amount": "100.00", "purpose": "CO-2026-0007",
         "credit": True, "counterparty": None, "reference": None},
        {"booking_date": "2026-07-21", "amount": "100.00", "purpose": "CO-2026-0007",
         "credit": True, "counterparty": None, "reference": None},
    ]
    res = match_transactions(txs, [_inv("CO-2026-0007", "200.00")])
    assert len(res["proposals"]) == 1
    assert "bereits zugeordnet" in res["unmatched"][0]["reason"]


def test_no_match_is_reported_not_dropped():
    txs = [{"booking_date": "2026-07-20", "amount": "12.34", "purpose": "Spende",
            "credit": True, "counterparty": None, "reference": None}]
    res = match_transactions(txs, [_inv("CO-2026-0011", "476.00")])
    assert res["proposals"] == []
    assert res["unmatched"][0]["reason"] == "keine passende offene Rechnung"
    assert res["transactions_total"] == 1


def test_reference_field_is_searched_too():
    txs = [{"booking_date": "2026-07-20", "amount": "476.00", "purpose": "Zahlung",
            "credit": True, "counterparty": None, "reference": "CO-2026-0011"}]
    res = match_transactions(txs, [_inv("CO-2026-0011", "476.00")])
    assert res["proposals"][0]["confidence"] == CONFIDENCE_EXACT


def test_prefixes_are_derived_from_invoices_when_not_given():
    txs = [{"booking_date": "2026-07-20", "amount": "10.00", "purpose": "RE-2026-0003",
            "credit": True, "counterparty": None, "reference": None}]
    res = match_transactions(txs, [_inv("RE-2026-0003", "10.00")])
    assert res["proposals"][0]["confidence"] == CONFIDENCE_EXACT
