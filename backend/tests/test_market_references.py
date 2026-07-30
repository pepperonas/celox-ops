"""Referenz-Ernte: Kunden eines Herstellers aus dem Referenzverzeichnis.

Die Beispiele sind **echte Fälle aus dem Lauf über die 20 größten Verzeichnisse** —
echte Negativbeispiele sind wertvoller als erfundene, und jeder dieser Fälle hat eine
Fassung des Verfahrens zu Fall gebracht.
"""
from app.services.market_references import (
    dedupe,
    ernte_aus_html,
    ernte_logowand,
    ist_kundenliste,
    marker_anteil,
    ohne_eigenen_namen,
    ohne_seitenrauschen,
    rauschschluessel,
    robots_erlaubt,
    saeubere_namen,
)


class TestRobots:
    def test_ohne_robots_erlaubt(self):
        # Abwesenheit einer Regel ist keine Verbotsregel.
        assert robots_erlaubt(None, "/referenzen") is True
        assert robots_erlaubt("", "/referenzen") is True

    def test_disallow_fuer_stern_greift(self):
        assert robots_erlaubt("User-agent: *\nDisallow: /referenzen", "/referenzen/") is False

    def test_regel_fuer_anderen_agenten_greift_nicht(self):
        assert robots_erlaubt("User-agent: Googlebot\nDisallow: /", "/referenzen") is True

    def test_laengste_regel_gewinnt(self):
        # So steht es im Standard: die spezifischere Regel entscheidet.
        txt = "User-agent: *\nDisallow: /\nAllow: /referenzen"
        assert robots_erlaubt(txt, "/referenzen/kunden") is True
        assert robots_erlaubt(txt, "/intern") is False


class TestNamen:
    def test_entities_werden_dekodiert(self):
        # Ohne Dekodierung landete „GmbH &amp; Co. KG" so in der Datenbank.
        assert saeubere_namen("Spandauer Velours GmbH &amp; Co. KG") == "Spandauer Velours GmbH & Co. KG"
        assert saeubere_namen("Trinkwasser GmbH &quot;ETW&quot;") == 'Trinkwasser GmbH "ETW"'

    def test_produktname_vor_dem_logo_faellt_weg(self):
        # HOPPE beschriftet jedes Kundenlogo mit „Wartungsplaner Logo <Firma>" —
        # der Produktname stand vor jedem der 1226 Namen.
        assert saeubere_namen("Wartungsplaner Logo BDL Untermain GmbH") == "BDL Untermain GmbH"
        assert saeubere_namen("Logo Siemens AG") == "Siemens AG"

    def test_deko_und_navigation_raus(self):
        for roh in ["Logo", "icon-arrow", "Pfeil nach rechts", "Lösungen", "Preise",
                    "CRM", "Übersicht", "Karriere", "Kontakt"]:
            assert saeubere_namen(roh) is None, roh

    def test_saetze_sind_keine_namen(self):
        assert saeubere_namen("Wir digitalisieren Ihre Prozesse von Anfang bis Ende.") is None

    def test_gepunktete_rechtsformen_zaehlen_mit(self):
        """Ein `\\b` hinter einem Punkt kann nicht greifen.

        Nach dem Punkt in „S.A." steht kein Wortzeichen, also gibt es dort keine
        Wortgrenze — das Muster lief nie an. Folge: Textlisten verloren diese Firmen,
        und in `market_contacts` wäre „Vertreten durch: Muster S.A." als
        Geschäftsführer durchgegangen. Beim Testen der Bewertung aufgefallen.
        """
        from app.services.market_references import ist_firmenname
        for name in ["Air Liquide S.A.", "Meier e. K.", "Turnverein e. V.",
                     "Philips B.V.", "Muster GmbH"]:
            assert ist_firmenname(name, streng=True) is True, name

    def test_zu_kurz_und_ohne_buchstaben(self):
        assert saeubere_namen("AB") is None
        assert saeubere_namen("12345") is None


class TestKundenlisteErkennen:
    # Aus der echten ADITO-Seite: ALLE „Namen" waren Menü- und Produktbegriffe.
    ADITO_NAV = ["Kontaktmanagement", "Vertrieb", "Marketing", "Service", "Collaboration",
                 "SRM", "CRM", "Vorteile", "Künstliche Intelligenz", "Schnittstellen",
                 "Customizing", "Cloud", "Preise", "CRM-Strategie"]
    # Aus der echten SER-Group-Seite: echte Konzerne, aber kaum Rechtsformen.
    SER_MARKEN = ["Deutsche Bahn AG", "Allianz GI Frankfurt", "Eli Lilly", "DHL Express",
                  "GLS", "Helvetia", "Randstad", "SEW-Eurodrive", "Kühne + Nagel",
                  "Mercedes AMG", "Liqui Moly"]

    def test_markenliste_hat_niedrigen_rechtsform_anteil(self):
        """Warum der Rechtsform-Anteil KEIN Tor sein darf.

        Große Marken tragen keine Rechtsform. Als Tor hätte er genau die
        hochwertigste Liste verworfen — die 169 Konzerne der SER Group kamen auf 24 %.
        """
        assert marker_anteil(self.SER_MARKEN) < 0.3
        ok, _ = ist_kundenliste(self.SER_MARKEN)
        assert ok is True

    def test_navigation_wird_ueber_das_seitenrauschen_erkannt(self):
        """Und warum die Menge allein auch nicht reicht.

        14 Menüpunkte sehen wie eine Liste aus. Erst der Abzug dessen, was auch auf
        der Startseite steht, trennt sie — Navigation ist auf jeder Seite, Kunden nur
        im Verzeichnis.
        """
        ok, _ = ist_kundenliste(self.ADITO_NAV)
        assert ok is True                                    # allein nicht erkennbar
        rest = ohne_seitenrauschen(self.ADITO_NAV, rauschschluessel(self.ADITO_NAV))
        assert rest == []                                    # nach Abzug bleibt nichts
        assert ist_kundenliste(rest)[0] is False

    def test_kunden_ueberleben_den_abzug(self):
        # Gegenprobe: Der Abzug darf die Kunden nicht mitnehmen.
        startseite = rauschschluessel(["Lösungen", "Preise", "Über uns"])
        rest = ohne_seitenrauschen(self.SER_MARKEN, startseite)
        assert len(rest) == len(self.SER_MARKEN)

    def test_zu_wenig_ist_keine_liste(self):
        assert ist_kundenliste(["A GmbH", "B AG"])[0] is False


class TestErnte:
    def test_logowand_liest_alt_texte(self):
        html = ('<img src="a.png" alt="Aesculap AG">'
                '<img src="b.png" alt="ABUS Kransysteme GmbH">'
                '<img src="c.png" alt="Logo">')
        assert ernte_logowand(html) == ["Aesculap AG", "ABUS Kransysteme GmbH"]

    def test_eigener_name_faellt_raus(self):
        # Auf der Vertec-Seite stand „Vertec Gruppe" als erster „Kunde".
        namen = ["Vertec Gruppe", "Zühlke Engineering AG", "Walder Wyss AG"]
        assert ohne_eigenen_namen(namen, "Vertec AG") == ["Zühlke Engineering AG", "Walder Wyss AG"]

    def test_dedupe_ignoriert_schreibweise(self):
        assert dedupe(["Siemens AG", "SIEMENS AG", "Bosch GmbH"]) == ["Siemens AG", "Bosch GmbH"]

    def test_ganzer_durchlauf_mit_rauschabzug(self):
        start = '<img alt="Lösungen"><img alt="Referenzen"><img alt="Musterprodukt">'
        # Bewusst NICHT „Kunde N GmbH" als Fixture: Das Beiwort „Kunde" wird korrekt
        # abgeschnitten („Kunde: Siemens" → „Siemens"), der Test hätte den Code
        # fälschlich beschuldigt.
        firmen = [f"Betrieb {b} GmbH" for b in "ABCDEFGHIJ"]
        ref = start + "".join(f'<img alt="{f}">' for f in firmen)
        rausch = rauschschluessel(dedupe(ernte_logowand(start)))
        e = ernte_aus_html(ref, "https://hersteller.de/referenzen", 10, "Hersteller AG", rausch)
        assert e.namen == firmen
        assert e.form == "logowand"

    def test_leere_seite_liefert_nichts(self):
        e = ernte_aus_html("<html><body></body></html>", "https://x.de/", 100, "X")
        assert e.namen == []
        assert "zu wenig" in e.verdikt
