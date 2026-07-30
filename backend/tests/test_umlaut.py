"""Transliterierte Umlaute zurückverwandeln.

Alle Fälle hier sind **echte Wörter aus dem Katalog** — die Fehltreffer wurden beim
Durchsehen der 623 im Bestand gemessenen Kandidaten gefunden, nicht erfunden.
"""
from app.services.umlaut import entschluessele, entschluessele_liste, wort_zurueck


class TestZurueck:
    def test_die_haeufigsten_faelle(self):
        for roh, soll in [
            ('Schaetzung', 'Schätzung'), ('fuer', 'für'), ('ueber', 'über'),
            ('Oeffentlicher', 'Öffentlicher'), ('Muenchen', 'München'),
            ('Geschaeftsfuehrung', 'Geschäftsführung'), ('Aerzte', 'Ärzte'),
            ('Qualitaetsmanagement', 'Qualitätsmanagement'), ('Loesung', 'Lösung'),
            ('Ueberstundenzuschlaege', 'Überstundenzuschläge'),
        ]:
            assert wort_zurueck(roh) == soll, roh

    def test_legitime_folgen_bleiben(self):
        """Die Wörter, die eine blinde Regel zerstören würde.

        Alle stehen im Bestand: „manuell" wäre „manüll" geworden, „Lead-Quelle" zu
        „Lead-Qülle".
        """
        for roh in ['manuell', 'manuelle', 'aktuell', 'aktueller', 'neue', 'neuer',
                    'Steuerberatung', 'Workflow-Steuerung', 'Quellen', 'Quellsysteme',
                    'Lead-Quelle', 'Termintreue', 'Objektbetreuer', 'Individuelle',
                    'Datenquellen', 'Fertigungssteuerung']:
            assert wort_zurueck(roh) == roh, roh

    def test_qu_ist_immer_ein_digraph(self):
        """Nach `q` ist `ue` NIE ein Umlaut — eine Regel statt einer Wortliste.

        Ohne sie wurde aus „Frequenz" „Freqünz" und aus „bequemsten" „beqümsten".
        Beim Durchsehen der echten Daten gefunden.
        """
        for roh in ['Frequenz', 'Frequenzen', 'bequemsten', 'Sequenz', 'Konsequenzen',
                    'konsequent', 'liquide']:
            assert wort_zurueck(roh) == roh, roh
        # Gegenprobe: „äquivalent" IST transliteriert und muss trotzdem greifen.
        assert wort_zurueck('aequivalent') == 'äquivalent'

    def test_adressen_bleiben_unangetastet(self):
        """In `blueant.de` steckt ein Name, kein Umlaut."""
        for roh in ['blueant.de', 'https://blueant.de/referenzen', 'www.mueller.de',
                    'http://haeuser.example.com/x']:
            assert wort_zurueck(roh) == roh, roh

    def test_zusammensetzung_positionsgenau(self):
        """Eine Ausnahme schützt die FOLGE, nicht das ganze Wort.

        Die erste Fassung übersprang das komplette Wort: „Betreuungskraefte" und
        „Aktualisierungsvorschlaege" blieben unkorrigiert, obwohl ihr `ae`
        transliteriert ist.
        """
        assert wort_zurueck('Betreuungskraefte') == 'Betreuungskräfte'
        assert wort_zurueck('Aktualisierungsvorschlaege') == 'Aktualisierungsvorschläge'
        assert wort_zurueck('Steuerungsvorschlaege') == 'Steuerungsvorschläge'

    def test_ss_wird_nicht_angefasst(self):
        # Dort ist die Umkehrung mehrdeutig („dass", „Prozess", „Adresse"), und im
        # Bestand gibt es keinen Fall. Ein Riegel, der nichts repariert, aber Text
        # kaputtmachen kann, gehört nicht in den Code.
        for roh in ['Prozess', 'Adresse', 'dass', 'Messung', 'Schluessel']:
            assert 'ß' not in wort_zurueck(roh), roh


class TestText:
    def test_ganzer_satz(self):
        assert entschluessele(
            'Taegliche Zeitbuchung wird nachtraeglich rekonstruiert.'
        ) == 'Tägliche Zeitbuchung wird nachträglich rekonstruiert.'

    def test_satzzeichen_und_klammern_bleiben(self):
        assert entschluessele('Pruefung (Qualitaet) — 5-10 Min/Tag!') \
            == 'Prüfung (Qualität) — 5-10 Min/Tag!'

    def test_gemischter_satz_mit_legitimen_woertern(self):
        assert entschluessele('Manuelle Pruefung der aktuellen Schaetzung') \
            == 'Manuelle Prüfung der aktuellen Schätzung'

    def test_leer_und_none(self):
        assert entschluessele(None) is None
        assert entschluessele('') == ''

    def test_liste(self):
        assert entschluessele_liste(['Pruefung', 'manuell', None]) \
            == ['Prüfung', 'manuell', None]
        assert entschluessele_liste(None) is None
        assert entschluessele_liste([]) == []
