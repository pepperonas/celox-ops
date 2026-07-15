"""DB-freie Tests für das Outreach-Modul: Seed-Vollständigkeit + Konsistenz."""
from app.models.outreach_template import OutreachCategory, OutreachChannel
from app.schemas.outreach import OutreachTemplateCreate
from app.services.outreach_seed import default_templates

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
    # 3 Kanäle × 7 Rubriken × 3 = 63
    assert len(seeds) == 63
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


def test_sort_order_is_zero_based_per_group():
    seeds = default_templates()
    groups: dict[tuple, list[int]] = {}
    for t in seeds:
        groups.setdefault((t["channel"], t["category"]), []).append(t["sort_order"])
    for key, orders in groups.items():
        assert sorted(orders) == list(range(len(orders))), f"sort_order Lücke bei {key}"
