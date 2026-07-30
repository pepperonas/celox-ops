"""Bewertung der Referenzkunden — die Reihenfolge muss nachrechenbar sein.

Der Score ist keine Wahrheitsbehauptung über die Lukrativität einer Firma (die Daten
geben das nicht her), sondern eine offengelegte Ordnung über die Signale, die
vorliegen. Diese Tests halten fest, WELCHE Signale zählen und mit welchem Gewicht.
"""
from app.services.market_reference_scoring import (
    W_BAUSTEIN,
    W_MEHRFACH_JE_SYSTEM,
    W_MEHRFACH_MAX,
    W_WEBSITE,
    bewerte,
    gesamt_score,
    orgtyp,
    score_teile,
    sortiere,
)


class TestOrgtyp:
    def test_oeffentliche_traeger(self):
        for name in ["Stadtwerke Achim AG", "Klinikum Fulda gGmbH", "Universität Passau",
                     "Landkreis Rotenburg", "Sparkasse Köln", "AOK Bayern",
                     "Kreiskrankenhaus Freiberg gGmbH"]:
            assert orgtyp(name) == "oeffentlich", name

    def test_traegerschaft_schlaegt_rechtsform(self):
        # „Klinikum … gGmbH" ist beides — die Trägerschaft ist die wichtigere Angabe.
        assert orgtyp("Klinikum Fulda gGmbH") == "oeffentlich"

    def test_konzernhinweise(self):
        for name in ["Deutsche Bahn AG", "Bernard Krone Holding SE & Co. KG",
                     "STP Group", "Air Liquide S.A."]:
            assert orgtyp(name) == "konzern", name

    def test_mittelstand(self):
        for name in ["Muster Ingenieure GmbH", "Schmidt & Sohn KG", "Meier e. K."]:
            assert orgtyp(name) == "mittelstand", name

    def test_unbekannt_statt_geraten(self):
        # Ein Markenname ohne Rechtsform lässt sich nicht einordnen — dann heißt es
        # ehrlich „unbekannt" und nicht irgendwas.
        for name in ["GLS", "Randstad", "Edeka", "", None]:
            assert orgtyp(name) == "unbekannt", name


class TestScoreTeile:
    def test_ein_system_gibt_keine_mehrfachpunkte(self):
        t = score_teile(systeme=1, hat_baustein=False, produkt_score=0, hat_website=False)
        assert t["mehrfachnutzung"] == 0
        assert gesamt_score(t) == 0

    def test_mehrfachnutzung_ist_das_staerkste_signal(self):
        # Das einzige echte Pro-Kunde-Signal: mehr Systeme = mehr Integrationsschmerz
        # und zwei Gesprächseinstiege statt einem.
        zwei = score_teile(systeme=2, hat_baustein=False, produkt_score=0, hat_website=False)
        assert zwei["mehrfachnutzung"] == W_MEHRFACH_JE_SYSTEM
        assert zwei["mehrfachnutzung"] > W_BAUSTEIN

    def test_mehrfachnutzung_ist_gedeckelt(self):
        viele = score_teile(systeme=9, hat_baustein=False, produkt_score=0, hat_website=False)
        assert viele["mehrfachnutzung"] == W_MEHRFACH_MAX

    def test_umfeld_ist_abgeschwaecht(self):
        # Der Produkt-Score beschreibt das Umfeld, nicht die Firma — er darf die
        # firmeneigenen Signale nicht überstimmen.
        t = score_teile(systeme=1, hat_baustein=False, produkt_score=100, hat_website=False)
        assert t["umfeld"] == 20
        assert t["umfeld"] < W_MEHRFACH_JE_SYSTEM

    def test_website_ist_ansprechbarkeit_kein_qualitaetsmerkmal(self):
        t = score_teile(systeme=1, hat_baustein=False, produkt_score=0, hat_website=True)
        assert t["ansprechbar"] == W_WEBSITE
        assert W_WEBSITE < W_BAUSTEIN

    def test_score_ist_die_summe_der_teile(self):
        # Nachrechenbarkeit ist der Sinn der Zerlegung.
        t = score_teile(systeme=2, hat_baustein=True, produkt_score=80, hat_website=True)
        assert gesamt_score(t) == min(100, sum(t.values()))
        assert gesamt_score(t) == min(100, 35 + 20 + 16 + 5)

    def test_score_bleibt_in_0_bis_100(self):
        hoch = score_teile(systeme=99, hat_baustein=True, produkt_score=100, hat_website=True)
        assert gesamt_score(hoch) == 100
        niedrig = score_teile(systeme=0, hat_baustein=False, produkt_score=-5, hat_website=False)
        assert gesamt_score(niedrig) == 0


class TestBewerte:
    def test_liefert_score_teile_und_typ(self):
        b = bewerte(company="Stadtwerke Achim AG", systeme=2, hat_baustein=True,
                    produkt_score=70, hat_website=False)
        assert b["orgtyp"] == "oeffentlich"
        assert b["systeme"] == 2
        assert b["score"] == b["score"] and sum(b["score_teile"].values()) == b["score"]

    def test_orgtyp_fliesst_NICHT_in_den_score(self):
        """Die wichtigste Zusicherung dieser Datei.

        Ob ein Klinikum lohnender ist als ein Maschinenbauer, hängt am Angebot und am
        Vertriebsweg — das kann der Code nicht wissen. Der Typ ist Kennzeichen und
        Filter, nie Punktwert.
        """
        gleich = dict(systeme=2, hat_baustein=True, produkt_score=70, hat_website=True)
        a = bewerte(company="Stadtwerke Achim AG", **gleich)
        b = bewerte(company="Muster Ingenieure GmbH", **gleich)
        c = bewerte(company="GLS", **gleich)
        assert a["score"] == b["score"] == c["score"]
        assert {a["orgtyp"], b["orgtyp"], c["orgtyp"]} == {"oeffentlich", "mittelstand", "unbekannt"}


class TestSortierung:
    ZEILEN = [
        {"company": "Beta GmbH", "score": 40, "systeme": 1},
        {"company": "Alpha AG", "score": 40, "systeme": 3},
        {"company": "Gamma KG", "score": 75, "systeme": 2},
    ]

    def test_standard_ist_score_absteigend(self):
        assert [z["company"] for z in sortiere(self.ZEILEN, "score")][0] == "Gamma KG"

    def test_gleicher_score_wird_ueber_den_namen_entschieden(self):
        # Ohne festen Zweitschlüssel wechselte die Reihenfolge zwischen zwei
        # Seitenaufrufen — bei einer paginierten Liste heißt das: Zeilen verschwinden
        # oder erscheinen doppelt.
        out = [z["company"] for z in sortiere(self.ZEILEN, "score")]
        assert out == ["Gamma KG", "Alpha AG", "Beta GmbH"]

    def test_nach_systemen(self):
        assert [z["company"] for z in sortiere(self.ZEILEN, "systeme")][0] == "Alpha AG"

    def test_nach_name(self):
        assert [z["company"] for z in sortiere(self.ZEILEN, "company")] == [
            "Alpha AG", "Beta GmbH", "Gamma KG"]

    def test_laesst_die_eingabe_unveraendert(self):
        vorher = [z["company"] for z in self.ZEILEN]
        sortiere(self.ZEILEN, "score")
        assert [z["company"] for z in self.ZEILEN] == vorher
