"""Referenzkunde → Lead: der Verkaufswinkel des Marktradars.

Geprüft wird vor allem, dass das Briefing das enthält, was man im Gespräch braucht —
und dass es nichts behauptet, was nicht in den Daten steht.
"""
from types import SimpleNamespace

from app.models.market_reference import norm_company
from app.services.market_reference_pipeline import (
    LEAD_SOURCE,
    bausteine_fuer,
    briefing,
    lead_tags,
)


def produkt(**kw):
    basis = dict(catalog_id="proj-bcs", produkt="Projektron BCS", hersteller="Projektron GmbH",
                 kategorie="Projektmanagement / PSA", pains=["Zeiten werden freitags nachgetragen"],
                 ki=["Buchungsvorschläge aus Kalender und Tickets"], score=78)
    return SimpleNamespace(**{**basis, **kw})


def referenz(**kw):
    basis = dict(company="Muster Ingenieure GmbH", website=None,
                 source_url="https://www.projektron.de/referenzen/")
    return SimpleNamespace(**{**basis, **kw})


def baustein(nr, titel, ids, was=""):
    return SimpleNamespace(nr=nr, titel=titel, catalog_ids=ids, was=was)


class TestBausteine:
    def test_zuordnung_kommt_aus_dem_katalog(self):
        # Die Zuordnung steht im Recherchekatalog. Eine zweite Bewertung hier würde
        # zwangsläufig von der Recherche abweichen.
        bs = [baustein(10, "Zeiterfassungs-Assistent", ["proj-bcs", "andere"]),
              baustein(3, "Regelwerks-Assistent", ["ganz-andere"])]
        assert [b.nr for b in bausteine_fuer("proj-bcs", bs)] == [10]

    def test_ohne_treffer_leer(self):
        assert bausteine_fuer("proj-bcs", [baustein(1, "X", [])]) == []

    def test_leere_catalog_ids_stuerzen_nicht(self):
        assert bausteine_fuer("proj-bcs", [baustein(1, "X", None)]) == []


class TestBriefing:
    def test_nennt_software_und_beleg(self):
        text = briefing(referenz(), produkt(), [])
        assert "Projektron BCS" in text
        assert "Projektron GmbH" in text
        assert "https://www.projektron.de/referenzen/" in text

    def test_nennt_den_passenden_baustein(self):
        bs = [baustein(10, "Zeiterfassungs-Assistent", ["proj-bcs"],
                       was="Buchungsvorschläge aus echter Arbeit")]
        text = briefing(referenz(), produkt(), bs)
        assert "Baustein 10" in text
        assert "Zeiterfassungs-Assistent" in text

    def test_fehlende_website_wird_ausgesprochen(self):
        # Sonst sucht man im Lead nach einem Feld, das nie gefüllt war.
        text = briefing(referenz(website=None), produkt(), [])
        assert "Website unbekannt" in text

    def test_mit_website_kein_hinweis(self):
        text = briefing(referenz(website="https://muster.de"), produkt(), [])
        assert "Website unbekannt" not in text

    def test_behauptet_nichts_ohne_daten(self):
        # Ohne Pains und KI-Idee dürfen die Zeilen nicht mit leeren Werten erscheinen.
        text = briefing(referenz(), produkt(pains=None, ki=None, kategorie=None), [])
        assert "Handarbeit" not in text
        assert "Aufhänger" not in text
        assert "Kategorie" not in text


class TestTags:
    def test_marktradar_und_referenzkunde(self):
        tags = lead_tags(produkt())
        assert "Marktradar" in tags
        assert "Referenzkunde" in tags

    def test_keine_dubletten(self):
        tags = lead_tags(produkt())
        assert len(tags) == len(set(tags))


class TestNormCompany:
    def test_schreibweise_egal(self):
        assert norm_company("Siemens AG") == norm_company("SIEMENS  AG")

    def test_rechtsform_bleibt_teil_des_schluessels(self):
        # „Muster GmbH" und „Muster AG" können verschiedene Gesellschaften sein —
        # zusammenzuführen, was verschieden ist, wäre der teurere Fehler.
        assert norm_company("Muster GmbH") != norm_company("Muster AG")

    def test_leer_bleibt_leer(self):
        assert norm_company(None) == ""
        assert norm_company("···") == ""


def test_quelle_ist_unterscheidbar():
    # Wichtig fürs Reporting: Hersteller-Leads und Kunden-Leads müssen sich am
    # `source`-Feld trennen lassen.
    from app.services.market_pipeline import LEAD_SOURCE as HERSTELLER_QUELLE
    assert LEAD_SOURCE != HERSTELLER_QUELLE
