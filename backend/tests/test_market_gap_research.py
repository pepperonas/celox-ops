"""Integrität der Forum-/Community-Recherche für den Marktradar."""
from app.data.market_gap_research import GAP_RESEARCH, all_ids, entry_for
from app.services import market_import


REQUIRED = ("forum_pains", "vendor_gaps", "remedies")


def test_gap_research_covers_142_and_is_well_formed():
    assert len(GAP_RESEARCH) == 142
    assert len(all_ids()) == 142
    for cid, entry in GAP_RESEARCH.items():
        assert set(entry) >= set(REQUIRED), cid
        for key in REQUIRED:
            items = entry[key]
            assert isinstance(items, list) and 2 <= len(items) <= 5, (cid, key)
            assert all(isinstance(x, str) and len(x.strip()) >= 12 for x in items), (cid, key)


def test_researched_anchors_carry_specific_friction():
    """Die fünf web-recherchierten Anker müssen ihre Kernpunkte tragen."""
    p = entry_for("personio")
    blob = " ".join(p["forum_pains"] + p["vendor_gaps"]).lower()
    assert "support" in blob or "datev" in blob or "eaus" in blob or "eau" in blob

    bcs = entry_for("projektron-bcs")
    rem = " ".join(bcs["remedies"]).lower()
    assert "bcsbook" in rem or "kalender" in rem

    dw = entry_for("docuware")
    assert any("workflow" in x.lower() or "recht" in x.lower() for x in dw["forum_pains"])

    otrs = entry_for("otrs")
    assert any("zammad" in x.lower() or "klassifik" in x.lower() for x in
               otrs["forum_pains"] + otrs["vendor_gaps"] + otrs["remedies"])


def test_ops_felder_schuetzen_gap_research():
    assert "forum_pains" in market_import._OPS_FELDER
    assert "vendor_gaps" in market_import._OPS_FELDER
    assert "remedies" in market_import._OPS_FELDER
    assert "gap_researched_at" in market_import._OPS_FELDER
    for key in ("forum_pains", "vendor_gaps", "remedies"):
        assert key not in market_import._KATALOG_FELDER.values()


def test_entry_for_unknown_is_none():
    assert entry_for("gibt-es-nicht") is None
