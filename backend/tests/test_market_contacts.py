"""Kontakt-Extraktion für den Marktradar — DB- und netzfrei.

Der Schwerpunkt liegt bewusst auf dem **Nicht-Finden**. Die Anforderung war „keinen
erfundenen Schrott, im Zweifel weglassen"; ein Test, der nur Treffer prüft, würde
genau die gefährliche Richtung nicht absichern.
"""
from app.services.market_contacts import (
    extract_decision_maker,
    extract_employee_count,
    extract_phone,
    imprint_urls,
    vendor_origin,
)


class TestVendorOrigin:
    def test_origin_ohne_pfad(self):
        assert vendor_origin("https://firma.de/referenzen/kunden") == "https://firma.de"

    def test_port_und_subdomain_bleiben(self):
        assert vendor_origin("https://www.firma.de:8443/a/b") == "https://www.firma.de:8443"

    def test_ohne_url_nichts(self):
        assert vendor_origin(None) is None
        assert vendor_origin("") is None
        assert vendor_origin("kein-url") is None


class TestPhone:
    def test_tel_link_wird_bevorzugt(self):
        # Ein tel:-Link ist vom Seitenautor ausdrücklich als Rufnummer markiert —
        # die verlässlichste Quelle auf einer Seite.
        html = '<p>Fragen? <a href="tel:+49 30 1234567">anrufen</a></p>'
        wert, beleg = extract_phone(html)
        assert wert == "+49 30 1234567"
        assert beleg.startswith("tel:")

    def test_beschrifteter_text_als_rueckfall(self):
        wert, beleg = extract_phone("<div>Telefon: 030 / 123 45 67</div>")
        assert wert == "030 / 123 45 67"
        assert "Telefon" in beleg

    def test_nackte_zahlenfolge_wird_NICHT_zur_nummer(self):
        # Ohne Beschriftung ist eine Ziffernfolge genauso gut eine Postleitzahl,
        # eine Umsatzangabe oder eine Artikelnummer.
        assert extract_phone("<p>10115 Berlin, HRB 123456 B</p>") == (None, None)
        assert extract_phone("<p>Wir haben 2.800 Kunden in 80 Ländern</p>") == (None, None)

    def test_zu_wenige_ziffern_wird_verworfen(self):
        assert extract_phone('<a href="tel:123">x</a>')[0] is None

    def test_zusammengelaufener_block_wird_verworfen(self):
        # Wenn hinter der Nummer noch eine USt-IdNr klebt, ist der Wert unbrauchbar.
        assert extract_phone("<p>Telefon: 030123456789012345678901234</p>")[0] is None

    def test_leeres_html(self):
        assert extract_phone("") == (None, None)


class TestDecisionMaker:
    def test_geschaeftsfuehrer_mit_label(self):
        wert, beleg = extract_decision_maker(
            "<p><strong>Geschäftsführer:</strong><br>Dr. Anna Meier</p>")
        assert wert == "Dr. Anna Meier"
        assert "Geschäftsführer" in beleg

    def test_mehrere_namen_bleiben_zusammen(self):
        wert, _ = extract_decision_maker(
            "<p>Vertreten durch: Anna Meier und Bernd Schulz</p>")
        assert wert == "Anna Meier und Bernd Schulz"

    def test_weitere_bezeichnungen(self):
        for label in ["Geschäftsführung", "Inhaber", "Vorstand", "Vertretungsberechtigt"]:
            wert, _ = extract_decision_maker(f"<p>{label}: Clara Nowak</p>")
            assert wert == "Clara Nowak", label

    def test_registerangabe_wird_abgeschnitten(self):
        # Im Impressum steht die Vertretung direkt neben den Registerdaten.
        wert, _ = extract_decision_maker(
            "<p>Geschäftsführer: Anna Meier, Amtsgericht Berlin HRB 12345</p>")
        assert wert == "Anna Meier"

    def test_ohne_label_KEIN_name(self):
        # Ein Personenname allein kann jeder sein — der Vertriebsansprechpartner,
        # ein Autor, ein Referenzkunde.
        assert extract_decision_maker("<p>Anna Meier leitet unser Team</p>") == (None, None)

    def test_adresse_und_kontaktzeilen_werden_verworfen(self):
        for zeile in [
            "Vertreten durch: 10115 Berlin",
            "Geschäftsführung: info@firma.de",
            "Inhaber: https://firma.de",
            "Geschäftsführer: Telefon 030 123456",
        ]:
            assert extract_decision_maker(f"<p>{zeile}</p>") == (None, None), zeile

    def test_firma_ist_kein_geschaeftsfuehrer(self):
        # „Vertreten durch die Muster-Verwaltungs GmbH" ist juristisch korrekt, als
        # ANREDE aber unbrauchbar — und genau dafür wird das Feld benutzt. Diese
        # Fälle rutschen an der Namensprüfung vorbei (zwei großgeschriebene Wörter),
        # der Rechtsform-Filter ist hier die einzige Schranke. Per Mutationstest
        # belegt: ohne ihn fällt dieser Test.
        for zeile in [
            "Vertreten durch: Musterfirma GmbH",
            "Geschäftsführung: Beispiel Verwaltungs AG",
            "Inhaber: Muster Software e. K.",
            "Geschäftsführer: Amtsgericht Charlottenburg HRB 123456",
            "Vertreten durch: Musterstraße 1",
        ]:
            assert extract_decision_maker(f"<p>{zeile}</p>") == (None, None), zeile

    def test_einzelwort_wird_verworfen(self):
        # „Geschäftsführung: Vorstand" ist kein Name.
        assert extract_decision_maker("<p>Geschäftsführung: Vorstand</p>") == (None, None)

    def test_prosa_wird_verworfen(self):
        lang = "Die Geschäftsführung besteht aus " + "sehr vielen Personen " * 6
        assert extract_decision_maker(f"<p>{lang}</p>") == (None, None)


class TestEmployeeCount:
    def test_klare_angabe(self):
        wert, beleg = extract_employee_count("<p>Heute arbeiten 120 Mitarbeiter bei uns.</p>")
        assert wert == 120
        assert "120 Mitarbeiter" in beleg

    def test_ungefaehre_angabe_und_tausenderpunkt(self):
        assert extract_employee_count("<p>rund 1.250 Beschäftigte</p>")[0] == 1250
        assert extract_employee_count("<p>über 80 Mitarbeiterinnen</p>")[0] == 80

    def test_team_formulierung(self):
        assert extract_employee_count("<p>Ein Team aus 40 Spezialisten.</p>")[0] == 40

    def test_KUNDENZAHL_wird_nicht_zur_mitarbeiterzahl(self):
        # Der wichtigste Test. In diesem Datensatz sind ALLE 142 `kunden`-Werte
        # Reichweiten-Angaben — solche Sätze stehen auch auf den Startseiten.
        for satz in [
            "Wir betreuen 2.800 Mitarbeiter unserer Kunden.",
            "60.000 Anwender arbeiten täglich mit unserer Lösung.",
            "Über 15.000 Organisationen vertrauen uns.",
            "5.500 Installationen bei 2.800 Unternehmen.",
            "Die Software verwaltet 30.000 Beschäftigte.",
            "Wir erfassen die Zeiten von 900 Mitarbeitern.",
        ]:
            assert extract_employee_count(f"<p>{satz}</p>") == (None, None), satz

    def test_unplausible_groesse_wird_verworfen(self):
        assert extract_employee_count("<p>900000 Mitarbeitende</p>") == (None, None)

    def test_ohne_angabe_nichts(self):
        assert extract_employee_count("<p>Wir sind ein modernes Softwarehaus.</p>") == (None, None)
        assert extract_employee_count("") == (None, None)


class TestGrundregel:
    def test_jeder_wert_steht_woertlich_auf_der_seite(self):
        """Die Kernzusage: Extraktion kann nichts erfinden.

        Jeder zurückgegebene Wert muss als Teilzeichenfolge in der Quelle vorkommen
        (bei Telefon nach Normalisierung der Leerzeichen). Damit ist eine
        Halluzination technisch ausgeschlossen — im Unterschied zu einem Modell.
        """
        html = """<html><body>
          <p>Geschäftsführer: Dr. Anna Meier</p>
          <p>Telefon: 030 123 4567</p>
          <p>Unser Team aus 45 Kolleginnen und Kollegen.</p>
        </body></html>"""
        gf, _ = extract_decision_maker(html)
        tel, _ = extract_phone(html)
        anzahl, beleg = extract_employee_count(html)
        assert gf in html
        assert tel.replace(" ", "") in html.replace(" ", "")
        assert str(anzahl) in html
        assert beleg in " ".join(html.split()).replace("<p>", "").replace("</p>", "")


class TestImprintUrls:
    """Die Reihenfolge der Kandidaten entscheidet über die Trefferquote.

    Live gemessen: `lead_enrichment.contact_page_url` nimmt den ERSTEN Treffer auf
    impressum|kontakt — Footer listen „Kontakt" meist vorher. Bei Projektron und
    InLoox landete man dadurch auf `/kontakt/`, wo keine Vertretungsangabe steht,
    und die Geschäftsführung blieb bei 0 %.
    """

    def test_impressum_kommt_vor_kontakt(self):
        html = ('<a href="/kontakt/">Kontakt</a>'
                '<a href="/impressum/">Impressum</a>')
        urls = imprint_urls(html, "https://firma.de/")
        assert urls[0] == "https://firma.de/impressum/"
        assert "https://firma.de/kontakt/" in urls

    def test_ohne_impressum_link_wird_der_standardpfad_geraten(self):
        # Auf Seiten, deren Footer erst im Browser entsteht, steht im HTML kein Link.
        # Ein geratener Pfad ist unkritisch: Er liefert eine echte Seite, aus der
        # wörtlich gelesen wird, oder einen Fehlercode.
        urls = imprint_urls('<a href="/kontakt/">Kontakt</a>', "https://firma.de/")
        assert urls[0] == "https://firma.de/impressum"

    def test_fremde_hosts_und_pseudolinks_bleiben_draussen(self):
        html = ('<a href="https://andere.de/impressum">x</a>'
                '<a href="mailto:a@b.de">m</a><a href="#imprint">a</a>'
                '<a href="/imprint">y</a>')
        urls = imprint_urls(html, "https://firma.de/")
        assert urls == ["https://firma.de/imprint"]

    def test_gedeckelt_auf_drei_versuche(self):
        html = "".join(f'<a href="/impressum-{i}">x</a>' for i in range(9))
        assert len(imprint_urls(html, "https://firma.de/")) == 3
