"""DB-freie Tests für das Outreach-Modul: Seed-Vollständigkeit + Konsistenz."""
from app.models.outreach_template import OutreachCategory, OutreachChannel
from app.schemas.outreach import OutreachTemplateCreate
from app.services.outreach_seed import _SIG, default_templates

CHANNELS = [c.value for c in OutreachChannel]
CATEGORIES = [c.value for c in OutreachCategory]


def test_at_least_three_per_channel_category():
    seeds = default_templates()
    for ch in CHANNELS:
        for cat in CATEGORIES:
            n = sum(1 for t in seeds if t["channel"] == ch and t["category"] == cat)
            assert n >= 3, f"{ch}/{cat} hat nur {n} Templates (min. 3 erwartet)"


def test_total_count_and_enums_valid():
    seeds = default_templates()
    # 3 Kanäle × 11 Rubriken × 3 = 99
    assert len(seeds) == 99
    for t in seeds:
        assert t["channel"] in CHANNELS
        assert t["category"] in CATEGORIES
        # jedes Seed validiert gegen das Create-Schema (Enums, Pflichtfelder)
        OutreachTemplateCreate(**t)


def test_email_has_subject_and_signature_others_not():
    for t in default_templates():
        if t["channel"] == "email":
            assert t["subject"], f"E-Mail ohne Betreff: {t['title']}"
            assert "Martin Pfeffer" in t["body"] and "celox.io" in t["body"]
        else:
            assert t["subject"] is None


def test_templates_and_ai_share_one_signature():
    """Vorlagen und KI-Entwürfe müssen dieselbe Signatur tragen — sonst schickt
    derselbe Absender zwei verschiedene Visitenkarten, und eine Adressänderung
    wird an einer Stelle vergessen."""
    from app.services.email_signature import SIGNATURE
    from app.services.lead_email_ai import SIGNATURE as AI_SIGNATURE

    assert AI_SIGNATURE == SIGNATURE
    for t in default_templates():
        if t["channel"] == "email":
            assert t["body"].endswith(SIGNATURE), f"'{t['title']}' ohne Signatur"
        else:
            # LinkedIn/Telefon tragen bewusst KEINE Signatur: dort ist der
            # Absender aus dem Kontext klar, und ein Adressblock in einer
            # Direktnachricht wirkt wie ein Serienbrief.
            assert SIGNATURE not in t["body"]


def test_signature_starts_with_the_greeting_the_html_builder_detects():
    """`email_html.text_to_html_email` setzt den Signaturblock ab, indem es die
    Grußzeile sucht. Beginnt die Signatur mit etwas anderem, landet sie im
    Fließtext — ohne Trennlinie, mitten im Absatz."""
    from app.services.email_html import _SIG_RE
    from app.services.email_signature import SIGNATURE

    assert _SIG_RE.search(SIGNATURE), "Grußzeile wird vom HTML-Bau nicht erkannt"


def test_legacy_signature_is_no_longer_produced():
    """Der Alt-Text bleibt als Suchmuster für das Migrationsskript erhalten —
    aber kein neuer Seed darf ihn noch schreiben."""
    from app.services.email_signature import LEGACY_TEMPLATE_SIGNATURE

    for t in default_templates():
        assert LEGACY_TEMPLATE_SIGNATURE not in t["body"]


def test_phone_templates_have_all_four_sections():
    needed = ("## Einstieg", "## Nutzenargument", "## Einwandbehandlung", "## Abschluss")
    for t in default_templates():
        if t["channel"] == "phone":
            for sec in needed:
                assert sec in t["body"], f"Telefon-Template '{t['title']}' fehlt {sec}"


def test_phone_covers_the_new_objections():
    phone_text = "\n".join(t["body"] for t in default_templates() if t["channel"] == "phone")
    assert "zu klein" in phone_text
    assert "IT-Firma" in phone_text or "Entwickler" in phone_text
    assert "Versicherung" in phone_text


# --------------------------------------------------------------------------- #
#  Inhaltliche Leitplanken der drei Produktlinien (2026-07)
#
#  Warum als Test und nicht als Kommentar: Der Seed ist Verkaufstext, und
#  Verkaufstext wird nachträglich „geschärft". Genau dabei rutschen die Sätze
#  raus, die rechtlich tragen. Die Schwesterprodukte (celox-datenschutz,
#  celox-portal) sichern dieselben Grenzen bereits per CI-Gate ab; hier fehlten
#  sie.
# --------------------------------------------------------------------------- #

NEW_LINES = ("datenschutz_dsms", "portal_assessment", "bcsbook_zeit")

# Übernommen aus dem Wording-Gate von celox-datenschutz
# (frontend/src/content/landing/landing-gates.test.ts). Erlaubt bleibt die
# VERNEINUNG — „keine 100 % DSGVO-Konformität" ist eine ehrliche Aussage.
FORBIDDEN_MARKETING = (
    "rechtssicher", "bußgeldsicher", "100 % dsgvo-konform", "100% dsgvo-konform",
    "absolut sicher", "vollautomatisch", "zero-knowledge",
    "militärische verschlüsselung", "ende-zu-ende-verschlüsselt",
)
NEGATIONS = ("kein ", "keine ", "keinen ", "nicht ", "keiner ", "keinem ")


def test_no_forbidden_marketing_terms():
    for t in default_templates():
        text = f"{t['subject'] or ''}\n{t['body']}".lower()
        for term in FORBIDDEN_MARKETING:
            idx = text.find(term)
            while idx != -1:
                prefix = text[max(0, idx - 30):idx]
                assert any(n in prefix for n in NEGATIONS), (
                    f"'{t['title']}' behauptet '{term}' ohne Verneinung"
                )
                idx = text.find(term, idx + 1)


def test_portal_line_never_promises_certification():
    """Die Portal-Assessments sind eine Standortbestimmung. Ein Zertifizierungs-
    Versprechen wäre die teuerste Falschaussage im ganzen Modul — und mindestens
    ein Text muss die Grenze aktiv benennen, nicht nur nicht verletzen."""
    texts = [t for t in default_templates() if t["category"] == "portal_assessment"]
    for t in texts:
        low = t["body"].lower()
        for claim in ("wir zertifizieren", "zertifizierung ihres", "zertifiziert ihr"):
            assert claim not in low, f"'{t['title']}' verspricht eine Zertifizierung"
    joined = "\n".join(t["body"].lower() for t in texts)
    assert "keine zertifizierung" in joined
    # § 38 BSIG darf für die Chefsache-Schulung NICHT als erfüllt behauptet
    # werden (gleiche Regel wie im portal: legal.nis2.chefsacheClaim).
    assert "erfüllt § 38" not in joined


def test_bcsbook_line_states_the_bcs_prerequisite():
    """bcsbook bucht in ein VORHANDENES Projektron BCS. Fehlt der Hinweis, läuft
    die Ansprache bei jedem Lead ohne BCS ins Leere — und wirkt unseriös."""
    for t in default_templates():
        if t["category"] != "bcsbook_zeit":
            continue
        assert "BCS" in t["body"], f"'{t['title']}' nennt BCS nicht"
    phones = [t for t in default_templates()
              if t["category"] == "bcsbook_zeit" and t["channel"] == "phone"]
    for t in phones:
        einstieg = t["body"].split("## Nutzenargument")[0]
        assert "BCS" in einstieg, (
            f"Leitfaden '{t['title']}' qualifiziert BCS nicht im Einstieg"
        )


def test_bcsbook_roi_matches_the_public_brochure():
    """Die Broschüre rechnet öffentlich 15 min · 220 Tage · 60 € Vollkostensatz
    = 3.300 € je Person und Jahr. Weicht die Vorlage davon ab, widerspricht sich
    das Angebot beim selben Kunden."""
    joined = "\n".join(t["body"] for t in default_templates()
                       if t["category"] == "bcsbook_zeit")
    for token in ("3.300", "220", "60 Euro", "165.000", "55.000"):
        assert token in joined, f"ROI-Anker '{token}' fehlt"


def test_new_lines_quote_no_own_prices():
    """Bewusste Entscheidung: keine eigenen Preise in der Erstansprache — der
    Preis fällt im Gespräch. Kundenseitige Kosten (bcsbook-ROI) sind erlaubt,
    eigene Monats-/Jahrespreise nicht."""
    own_prices = ("99 €", "249 €", "499 €", "390 €", "29 €", "24 €", "490 €",
                  "590 €", "1.190 €", "2.390 €", "/Monat", "pro Monat")
    for t in default_templates():
        if t["category"] not in NEW_LINES:
            continue
        text = f"{t['subject'] or ''}\n{t['body']}"
        for p in own_prices:
            assert p not in text, f"'{t['title']}' nennt einen eigenen Preis ({p})"


def test_new_lines_end_with_a_question():
    """Jede Nachricht braucht eine Handlungsaufforderung. Ein Text, der mit einem
    Punkt endet, verlagert die Initiative auf den Empfänger — dort bleibt sie.

    Bei E-Mails hängt `default_templates()` die Signatur an, die Frage steht also
    davor; geprüft wird der letzte inhaltliche Absatz."""
    for t in default_templates():
        if t["category"] not in NEW_LINES:
            continue
        text = t["body"].split(_SIG)[0] if _SIG in t["body"] else t["body"]
        assert text.rstrip().endswith("?"), f"'{t['title']}' endet ohne Frage"


def test_bcsbook_phone_addresses_the_surveillance_objection():
    """Der erste echte Einwand bei automatischer Zeiterfassung ist nicht der
    Preis, sondern Überwachung. Fehlt die Antwort, stirbt das Gespräch dort."""
    joined = "\n".join(t["body"].lower() for t in default_templates()
                       if t["category"] == "bcsbook_zeit" and t["channel"] == "phone")
    assert "überwachung" in joined
    assert "lokal" in joined
    assert "ohne bestätigung" in joined or "bestätigt jede buchung" in joined


def test_sort_order_is_zero_based_per_group():
    seeds = default_templates()
    groups: dict[tuple, list[int]] = {}
    for t in seeds:
        groups.setdefault((t["channel"], t["category"]), []).append(t["sort_order"])
    for key, orders in groups.items():
        assert sorted(orders) == list(range(len(orders))), f"sort_order Lücke bei {key}"
