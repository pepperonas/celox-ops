"""Namensauflösung über Google Places — die Prüfung, die falsche Firmen fernhält.

Eine Places-Textsuche nach einem Firmennamen liefert bereitwillig eine *ähnlich*
heißende Firma. Eine falsche Website ist hier schlimmer als keine: Aus ihr folgt ein
falsches Impressum, also ein falscher Geschäftsführer und eine falsche Rufnummer.
"""
from app.services.market_reference_enrich import _bedeutsame_woerter, namen_passen


class TestNamenPassen:
    def test_gleicher_name(self):
        assert namen_passen("August Storck KG", "August Storck KG") is True

    def test_rechtsform_darf_fehlen(self):
        assert namen_passen("Stadtwerke Achim AG", "Stadtwerke Achim") is True
        assert namen_passen("Stadtwerke Achim", "Stadtwerke Achim AG") is True

    def test_zusatz_im_gefundenen_namen(self):
        # „Julius Zorn GmbH" ⊂ „Julius Zorn GmbH Juzo" — dieselbe Firma.
        assert namen_passen("Julius Zorn GmbH", "Julius Zorn GmbH Juzo") is True

    def test_EIN_wort_reicht_NICHT(self):
        """Der wichtigste Fall.

        „Tetra GmbH" (Fischfutter, Melle) und „Tetra Pak Deutschland GmbH" sind
        verschiedene Firmen. Mit Ein-Wort-Enthaltensein wäre das eine Übereinstimmung
        gewesen — und die falsche Website hätte einen falschen Geschäftsführer
        nachgezogen.
        """
        assert namen_passen("Tetra GmbH", "Tetra Pak Deutschland GmbH") is False
        assert namen_passen("Anschütz GmbH", "Raytheon Anschütz GmbH") is False

    def test_voellig_andere_firma(self):
        assert namen_passen("Aquatherm GmbH", "Meier Bau GmbH") is False

    def test_leere_eingaben(self):
        assert namen_passen("", "Muster GmbH") is False
        assert namen_passen("Muster GmbH", "") is False
        assert namen_passen(None, None) is False

    def test_rechtsform_allein_ist_keine_uebereinstimmung(self):
        # Sonst „passte" jede GmbH zu jeder anderen.
        assert namen_passen("Alpha GmbH", "Beta GmbH") is False


class TestBedeutsameWoerter:
    def test_rechtsformen_und_ortszusaetze_fallen_weg(self):
        # Sie kommen in tausenden Namen vor und würden fremde Firmen verbinden.
        assert _bedeutsame_woerter("Muster Technik GmbH & Co. KG") == ["muster", "technik"]
        assert _bedeutsame_woerter("Alpha Group Deutschland") == ["alpha"]

    def test_kurze_bestandteile_fallen_weg(self):
        assert "ab" not in _bedeutsame_woerter("AB Muster Werke")

    def test_zahlen_bleiben(self):
        assert "2000" in _bedeutsame_woerter("Technik 2000 GmbH")
