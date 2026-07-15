"""Seed-Inhalte für das Akquise-Nachrichten-Modul (outreach).

Positionierung: **IT-Sicherheit ist das führende Verkaufsthema**, Datenschutz/DSB
nur unterstützendes Anschlussprodukt (max. ein Nebensatz in E-Mail/LinkedIn, im
Telefonleitfaden als Cross-Sell am Gesprächsende). Absender: Martin Pfeffer,
celox.io, Berlin. Credentials: ISO 27001, BSI IT-Grundschutz, IHK-zert. DSB.

Platzhalter: {{anrede}} {{name}} {{firma}} {{branche}} {{aufhaenger}} {{risiko_branche}}.
Telefon-Bodies gliedern sich über ##-Überschriften (Einstieg/Nutzenargument/
Einwandbehandlung/Abschluss) — die UI rendert sie als einzeln kopierbare Abschnitte.

`default_templates()` ist eine reine Funktion (ohne DB) → unit-testbar.
"""

_SIG = "\n\nBeste Grüße\nMartin Pfeffer\ncelox.io · Berlin"


def _t(channel, category, title, body, subject=None, notes=None):
    return {"channel": channel, "category": category, "title": title,
            "subject": subject, "body": body.strip(), "notes": notes}


# --------------------------------------------------------------------------- #
#  E-MAIL (Body ohne Signatur — wird in default_templates() angehängt)
# --------------------------------------------------------------------------- #
_EMAIL = [
    # ---- Kaltakquise ----
    _t("email", "kaltakquise", "3 Lücken in 5 Minuten (KMU-GF)",
       """{{anrede}} {{name}},

bei {{branche}}-Betrieben wie {{firma}} finde ich fast immer drei Dinge in wenigen Minuten: veraltete Systeme mit bekannten Lücken, kein belastbares Backup und Konten ohne Zwei-Faktor-Schutz. Jedes davon reicht für {{risiko_branche}}.

Ich bin kein Berater, der einen PDF-Bericht hinterlässt — ich behebe die Findings selbst (Härtung, sichere Architektur). Arbeitsweise nach ISO 27001 und BSI-Grundschutz.

Vorschlag: ein kostenloser 15-Minuten-Security-Quick-Check per Call — konkrete Risiken für {{firma}}, keine Verkaufsschleife. Passt Ihnen diese oder nächste Woche?""",
       subject="{{firma}}: 3 Sicherheitslücken, die ich in 5 Minuten sehe",
       notes="Erstkontakt: konkret statt Selbstvorstellung. Die Zahl im Betreff weckt Neugier. Max. 120 Wörter."),
    _t("email", "kaltakquise", "Security zukaufen (Agentur)",
       """{{anrede}} {{name}},

wenn {{firma}} Websites oder Software für Kunden baut, kommt die Frage nach IT-Sicherheit und Nachweisen (ISO 27001, NIS2-Lieferkette) immer häufiger — oft mitten im Projekt.

Ich springe als Security-Partner ein: prüfen, härten, sichere Architektur — umgesetzt statt nur empfohlen. Ein Ansprechpartner, der Entwicklersprache spricht und liefert; auf Wunsch inkl. externem Datenschutzbeauftragten.

15 Minuten per Call, um auszuloten, wo ich Ihre Projekte entlaste? Ich richte mich nach Ihrem Kalender.""",
       subject="Security-Kompetenz für {{firma}}-Projekte – zubuchbar",
       notes="Zielgruppe Agentur/IT-Dienstleister: White-Label-Security. DSB nur Nebensatz."),
    _t("email", "kaltakquise", "Was ein Tag Stillstand kostet (Branche)",
       """{{anrede}} {{name}},

in {{branche}} hängt der Umsatz an laufenden Systemen — {{risiko_branche}} bedeutet nicht nur IT-Ärger, sondern verlorene Aufträge und Haftungsfragen.

Ich prüfe gezielt die Punkte, die bei {{firma}} den Betrieb lahmlegen könnten (Ransomware, Phishing, ungesicherte Zugänge), und setze die Absicherung selbst um — Beratung und Umsetzung aus einer Hand, dokumentiert nach BSI-Grundschutz.

Kostenloser 15-Minuten-Security-Quick-Check per Call — ich zeige Ihnen die drei dringlichsten Punkte. Wann passt es Ihnen?""",
       subject="{{branche}}: Was ein Tag Stillstand {{firma}} kostet",
       notes="Branchen-Aufhänger über {{risiko_branche}}. Business-Übersetzung: Auftragsverlust/Haftung."),

    # ---- Follow-up ----
    _t("email", "followup", "1 Tipp beigelegt (KMU-GF)",
       """{{anrede}} {{name}},

ich hake kurz nach — aber nicht mit leeren Händen: Der wirksamste Sofort-Schutz gegen Konto-Übernahmen ist Zwei-Faktor auf E-Mail und Buchhaltung. Kostet nichts, verhindert die häufigste Angriffsform.

Wenn Sie mögen, gehe ich im 15-Minuten-Call die weiteren Quick-Wins für {{firma}} durch. Sag ich Freitag oder lieber Anfang nächster Woche?""",
       subject="Kurz zu {{firma}}: 1 Tipp, der heute schon schützt",
       notes="Follow-up mit echtem Mehrwert statt „wollte nachhaken“."),
    _t("email", "followup", "Passend zum letzten Austausch",
       """{{anrede}} {{name}},

die Ransomware-Welle gegen kleinere {{branche}}-Betriebe zeigt genau das Muster, über das wir sprachen: Angreifer nehmen nicht mehr nur Großkonzerne ins Visier, sondern die, bei denen es schnell geht.

Mein Angebot steht: 15-Minuten-Security-Quick-Check für {{firma}}, kostenlos und konkret. Ein kurzes „ja“ genügt.""",
       subject="Passend zu unserem letzten Austausch, {{name}}",
       notes="Anlassbezogen, greift ein bekanntes Bedrohungsbild auf."),
    _t("email", "followup", "Nachfass Security-Partnerschaft (Agentur)",
       """{{anrede}} {{name}},

noch ein Gedanke: Gerade in Ausschreibungen wird der Security-Nachweis (ISO 27001, NIS2) zum K.-o.-Kriterium. Als zubuchbarer Partner liefere ich Ihnen genau diesen Nachweis — prüfbar und umgesetzt.

15 Minuten, um es an einem konkreten Projekt durchzuspielen? Ich passe mich Ihrem Kalender an.""",
       subject="{{firma}}: kurzer Nachfass zur Security-Partnerschaft"),

    # ---- Reaktivierung ----
    _t("email", "reaktivierung", "Seit unserem Kontakt hat sich X geändert",
       """{{anrede}} {{name}},

seit wir zuletzt sprachen, sind zwei Dinge konkreter geworden: NIS2 zieht Sicherheitsanforderungen über Lieferketten auch zu kleineren Betrieben, und Angriffe auf {{branche}} haben spürbar zugenommen.

Vielleicht ein guter Moment, den offenen Faden wieder aufzunehmen. Kostenloser 15-Minuten-Security-Quick-Check für {{firma}} — ich zeige, wo Sie heute stehen. Passt es diese Woche?""",
       subject="Seit unserem Kontakt hat sich für {{branche}} einiges geändert",
       notes="Reaktivierung mit konkretem Anlass (NIS2 + Bedrohungslage)."),
    _t("email", "reaktivierung", "Versicherer verlangen jetzt Nachweise",
       """{{anrede}} {{name}},

ich melde mich nochmal, weil sich die Ausgangslage geändert hat: Cyber-Versicherer verlangen inzwischen belegte Mindeststandards, sonst zahlen sie im Schadensfall nicht.

Genau da setze ich an — prüfen und umsetzen aus einer Hand. Sollen wir die 15 Minuten nachholen, die letztes Mal untergingen?""",
       subject="Kurzer Wiederanknüpfer, {{name}}"),
    _t("email", "reaktivierung", "Neuer Anlauf (Agentur)",
       """{{anrede}} {{name}},

unser Austausch ist eingeschlafen — das lag am Timing, nicht am Thema. Inzwischen fragen Endkunden bei Agenturen aktiv nach Security-Nachweisen.

Ich bleibe Ihr zubuchbarer Partner dafür. 15 Minuten, um zu schauen, wo es gerade brennt?""",
       subject="{{firma}} & Security: neuer Anlauf?"),

    # ---- Empfehlung ----
    _t("email", "empfehlung", "Referenz aus der Branche",
       """{{anrede}} {{name}},

ich habe zuletzt für einen {{branche}}-Betrieb die häufigsten Einfallstore geschlossen — von ungesicherten Fernzugängen bis zu fehlenden Backups. Ergebnis: auditfähiger Zustand, ohne den Betrieb auszubremsen.

Weil {{firma}} ähnlich aufgestellt ist: Wollen wir in 15 Minuten schauen, ob dieselben Punkte bei Ihnen relevant sind? Kostenlos und unverbindlich.""",
       subject="Durfte kürzlich {{branche}} absichern – passt das für {{firma}}?",
       notes="Referenz-Framing ohne Nennung von Interna."),
    _t("email", "empfehlung", "Über Empfehler eingeführt",
       """{{anrede}} {{name}},

[Empfehler] hat den Kontakt angeregt — ich habe dort die IT-Sicherheit auf einen prüfbaren Stand gebracht und offenbar Eindruck hinterlassen.

Für {{firma}} biete ich denselben Einstieg: kostenloser 15-Minuten-Security-Quick-Check, konkrete Findings statt Folien. Wann passt es Ihnen?""",
       subject="{{name}}, [Empfehler] meinte, ich soll mich melden",
       notes="[Empfehler] vor dem Senden durch echten Namen ersetzen."),
    _t("email", "empfehlung", "Referenz für Agentur",
       """{{anrede}} {{name}},

für eine Digitalagentur habe ich zuletzt die Kundenprojekte security-seitig abgesichert und die Nachweise für Ausschreibungen geliefert — ein Ansprechpartner, der entwickelt und härtet.

Das lässt sich auf {{firma}} übertragen. 15 Minuten, um es zu konkretisieren?""",
       subject="Security-Partner für {{firma}} – mit Referenz"),

    # ---- Angebot nachfassen ----
    _t("email", "angebot_nachfassen", "Risiko der Nicht-Entscheidung",
       """{{anrede}} {{name}},

ich verstehe, dass Security selten oben auf der Liste steht — bis etwas passiert. Der Haken: Die offenen Punkte aus meinem Angebot (u. a. {{aufhaenger}}) sind genau die, die im Ernstfall den Betrieb treffen.

Kein Druck — aber lassen Sie mich die Prioritäten in 10 Minuten einordnen, dann entscheiden Sie fundiert. Passt morgen?""",
       subject="Zu meinem Angebot für {{firma}} – kurz eingeordnet",
       notes="Risiko sachlich benennen, ohne Angstrhetorik."),
    _t("email", "angebot_nachfassen", "Bleibt das Angebot aktuell?",
       """{{anrede}} {{name}},

nur eine kurze Rückfrage, damit ich richtig plane: Ist die Absicherung für {{firma}} noch ein Thema für dieses Quartal?

Falls ja, halte ich einen Slot frei. Falls das Budget der Punkt ist, zeige ich Ihnen einen abgestuften Einstieg — man muss nicht alles auf einmal machen.""",
       subject="Bleibt mein Angebot für {{firma}} aktuell?"),
    _t("email", "angebot_nachfassen", "Letzter Anstoß",
       """{{anrede}} {{name}},

ich will nicht nerven — daher der letzte kurze Anstoß. Wenn Security bei {{firma}} gerade keine Priorität hat, ist das völlig in Ordnung; ich melde mich dann in ein paar Monaten wieder.

Falls doch: Ein „ja“ und wir halten die 15 Minuten fest.""",
       subject="Letzter Anstoß zu {{firma}}"),

    # ---- Security-Upsell (Bestandskunden) ----
    _t("email", "security_upsell", "Website läuft – wer schützt sie?",
       """{{anrede}} {{name}},

Ihre Website/Anwendung ist live und tut, was sie soll. Was oft fehlt: laufende Absicherung — Updates, Monitoring, Backups, ein jährlicher Check. Ungepatchte Systeme sind das häufigste Einfallstor.

Ich schnüre das als festes Paket: Wartung + Security-Monitoring + jährlicher Quick-Check, ein Ansprechpartner, planbare Kosten — auf Wunsch inkl. Datenschutz-Betreuung.

15 Minuten, um Ihren Retainer zu skizzieren?""",
       subject="{{firma}}: Ihre Website läuft – aber wer schützt sie?",
       notes="Bestandskunde Website → Security-Retainer. DSB als Nebensatz."),
    _t("email", "security_upsell", "Nach dem Go-Live absichern",
       """{{anrede}} {{name}},

nach dem Projekt endet die Verantwortung nicht — Abhängigkeiten veralten, neue Lücken werden bekannt. Statt Feuerwehr im Ernstfall schlage ich planbaren Schutz vor: Monitoring, regelmäßige Updates, jährlicher Security-Check.

Als Ihr Entwickler kenne ich das System — die Absicherung sitzt dadurch schneller. Sollen wir das Paket in 15 Minuten festzurren?""",
       subject="Nach dem Go-Live: {{firma}} dauerhaft absichern"),
    _t("email", "security_upsell", "Fester Security-Baustein",
       """{{anrede}} {{name}},

wir arbeiten schon zusammen — lassen Sie uns Security nicht dem Zufall überlassen. Ein schlanker Retainer deckt das Wichtigste ab: Überwachung, Updates, Reaktion im Fall der Fälle, jährliche Prüfung nach BSI-Grundschutz.

Ich mache Ihnen einen Vorschlag mit klarer Monatspauschale. 15 Minuten diese Woche?""",
       subject="Ein fester Security-Baustein für {{firma}}"),

    # ---- Security-Audit (Einstiegsprodukt) ----
    _t("email", "security_audit", "Kostenloser Quick-Check (KMU-GF)",
       """{{anrede}} {{name}},

als niedrigschwelligen Einstieg biete ich einen kostenlosen Security-Quick-Check: In 15 Minuten am Telefon gehe ich mit Ihnen die häufigsten Einfallstore für {{branche}} durch und nenne die drei dringlichsten Punkte für {{firma}} — konkret, ohne Fachchinesisch.

Kein Verkaufsgespräch: Sie bekommen eine klare Einordnung, ob und wo Handlungsbedarf besteht. Wann passt es Ihnen?""",
       subject="{{firma}}: kostenloser Security-Quick-Check (15 Min)",
       notes="Einstiegsprodukt. Betont: kostenlos, konkret, kein Verkauf."),
    _t("email", "security_audit", "Strukturiertes Audit",
       """{{anrede}} {{name}},

wenn Kunden oder Versicherer Nachweise verlangen, hilft kein Bauchgefühl. Mein Security-Audit prüft {{firma}} strukturiert nach BSI-Grundschutz-/ISO-27001-Logik — und ich liefere nicht nur den Bericht, sondern behebe die Findings auf Wunsch gleich mit.

Start ist der kostenlose 15-Minuten-Quick-Check, damit Sie den Umfang einschätzen können. Passt diese Woche?""",
       subject="Auditfähige IT-Sicherheit für {{firma}} – strukturiert"),
    _t("email", "security_audit", "NIS2-Nachweis (Lieferkette)",
       """{{anrede}} {{name}},

NIS2 zieht Anforderungen über die Lieferkette — auch zu Dienstleistern wie {{firma}}. Ein dokumentiertes Security-Audit macht Sie gegenüber Ihren Kunden nachweisfähig.

Ich prüfe und setze um, aus einer Hand. Einstieg: kostenloser 15-Minuten-Quick-Check. Wann passt es?""",
       subject="NIS2-Nachweis für {{firma}} – prüfbar gemacht"),

    # ---- KI-Automatisierung (Prozessautomatisierung, DSB als Differenzierer) ----
    _t("email", "ki_automatisierung", "Rechnungseingang automatisieren",
       """{{anrede}} {{name}},

Betriebe wie {{firma}} verlieren oft 10–20 Stunden pro Woche durch das manuelle Abtippen von Rechnungen, Lieferscheinen und Auftragsbestätigungen — plus die Fehlerkosten, wenn dabei etwas schiefgeht.

Ich automatisiere genau das mit KI: Dokument rein, geprüfte strukturierte Daten raus, direkt in {{zielsystem}}. Ohne Cloud-Zwang, ohne dass Ihre Daten unkontrolliert an US-Anbieter fließen.

Was mich von anderen KI-Dienstleistern unterscheidet: Ich bin IHK-zertifizierter Datenschutzbeauftragter (ISO 27001, BSI IT-Grundschutz) und Senior-Entwickler. Die DSGVO-Frage, an der KI-Projekte im Mittelstand meist scheitern, löse ich gleich mit.

Mein Vorschlag: ein Prozess-Audit mit DSGVO-Check — Festpreis {{audit_preis}}, Ergebnis nach {{audit_dauer}}, inkl. konkreter Automatisierungsliste mit ROI in Euro.

15 Minuten diese Woche? Ich zeige live, wie eine Ihrer Beispielrechnungen in Sekunden zu strukturierten Daten wird.""",
       subject="Wie viele Stunden pro Woche kostet Sie Ihr Rechnungseingang?",
       notes="Hero-Use-Case Rechnungseingang. {{zielsystem}}=DATEV/ERP, {{audit_preis}}/{{audit_dauer}} pro Kunde setzen."),
    _t("email", "ki_automatisierung", "E-Mail-Triage automatisieren",
       """{{anrede}} {{name}},

wenn bei {{firma}} täglich Anfragen, Bestellungen und Rechnungen im selben Postfach landen, kostet allein das Sortieren und Weiterleiten Stunden — und Wichtiges bleibt liegen.

Ich automatisiere die E-Mail-Triage mit KI: eingehende Mails werden erkannt, kategorisiert und an die richtige Stelle bzw. in {{zielsystem}} geroutet; Sonderfälle landen zur Prüfung bei einem Menschen (Human-in-the-Loop).

Der Unterschied zu anderen KI-Anbietern: Als IHK-zertifizierter DSB (ISO 27001) baue ich das von Anfang an DSGVO-konform, inkl. Dokumentation für Ihre Nachweispflichten.

Einstieg ist ein Prozess-Audit mit DSGVO-Check zum Festpreis {{audit_preis}} (Ergebnis nach {{audit_dauer}}). 15 Minuten diese Woche für eine Live-Demo?""",
       subject="{{firma}}: Wer sortiert bei Ihnen den Posteingang?",
       notes="Modularer Use-Case E-Mail-Triage. Alternativen: Support-Bot, Reporting."),
    _t("email", "ki_automatisierung", "Manuelle Dateneingabe (ROI-Winkel)",
       """{{anrede}} {{name}},

jede manuell abgetippte Rechnung, jeder Lieferschein, jede Auftragsbestätigung kostet Zeit und produziert Tippfehler. Bei {{firma}} summiert sich das schnell auf einen Mitarbeitertag pro Woche.

Ich setze KI genau dort an: Dokument rein, geprüfte strukturierte Daten in {{zielsystem}} raus. Individuell und wartbar (Python/FastAPI), keine fragile Low-Code-Blackbox.

Weil KI-Projekte im Mittelstand meist an der DSGVO scheitern: Ich bin zertifizierter DSB und liefere die Compliance-Dokumentation mit.

Starten wir mit einem Prozess-Audit (Festpreis {{audit_preis}}, {{audit_dauer}}) — Sie bekommen eine priorisierte Liste mit ROI in Euro. 15 Minuten für den Überblick?""",
       subject="Manuelle Dateneingabe bei {{firma}} — was kostet sie wirklich?"),
]


# --------------------------------------------------------------------------- #
#  LINKEDIN (max. 60 Wörter, kein Betreff/keine Signatur)
# --------------------------------------------------------------------------- #
_LINKEDIN = [
    # Kaltakquise
    _t("linkedin", "kaltakquise", "3 Einfallstore (KMU-GF)",
       "{{anrede}} {{name}}, bei {{branche}}-Betrieben finde ich meist in Minuten drei offene Einfallstore — veraltete Systeme, fehlende Backups, Logins ohne 2FA. Ich prüfe UND behebe (kein PDF-Berater), Arbeitsweise nach ISO 27001. Lust auf einen kostenlosen 15-Min-Security-Quick-Check für {{firma}}?",
       notes="LinkedIn: kurz, konkret, kein Lebenslauf. ≤60 Wörter."),
    _t("linkedin", "kaltakquise", "Security-Türöffner (Agentur)",
       "{{anrede}} {{name}}, {{firma}} baut für Kunden — und Security-Nachweise (ISO 27001, NIS2) werden zum Projekt-Türöffner. Ich bin als Security-Partner zubuchbar: prüfen, härten, umsetzen. Entwicklersprache inklusive. 15 Minuten, um es an einem Projekt durchzuspielen?"),
    _t("linkedin", "kaltakquise", "Branchen-Risiko",
       "{{anrede}} {{name}}, in {{branche}} bedeutet {{risiko_branche}} verlorene Aufträge, nicht nur IT-Ärger. Ich schließe genau diese Lücken — Beratung und Umsetzung aus einer Hand. Kostenloser 15-Min-Quick-Check für {{firma}}?"),
    # Follow-up
    _t("linkedin", "followup", "Quick-Win beigelegt",
       "{{anrede}} {{name}}, kurzer Nachfass mit Mehrwert: 2FA auf E-Mail und Buchhaltung stoppt die häufigste Angriffsform — kostenlos umsetzbar. Die weiteren Quick-Wins für {{firma}} zeige ich in 15 Minuten. Diese Woche?"),
    _t("linkedin", "followup", "Bedrohungslage",
       "{{anrede}} {{name}}, die aktuelle Ransomware-Welle trifft genau kleinere {{branche}}-Betriebe. Mein Angebot steht: kostenloser 15-Min-Security-Quick-Check für {{firma}}. Ein kurzes Ja genügt."),
    _t("linkedin", "followup", "Ausschreibungs-Nachweis (Agentur)",
       "{{anrede}} {{name}}, noch ein Gedanke: In Ausschreibungen wird der Security-Nachweis zum K.-o.-Kriterium. Als zubuchbarer Partner liefere ich ihn prüfbar. 15 Minuten dazu?"),
    # Reaktivierung
    _t("linkedin", "reaktivierung", "NIS2 + Bedrohungslage",
       "{{anrede}} {{name}}, seit unserem letzten Austausch zieht NIS2 die Anforderungen auch zu kleineren Betrieben — und Angriffe auf {{branche}} nehmen zu. Guter Moment, um anzuknüpfen? Kostenloser 15-Min-Check für {{firma}}."),
    _t("linkedin", "reaktivierung", "Versicherer-Standards",
       "{{anrede}} {{name}}, Cyber-Versicherer verlangen inzwischen belegte Mindeststandards — sonst keine Zahlung im Schadensfall. Genau da helfe ich. Holen wir die 15 Minuten nach?"),
    _t("linkedin", "reaktivierung", "Faden wieder aufnehmen (Agentur)",
       "{{anrede}} {{name}}, unser Faden ist eingeschlafen — lag am Timing. Endkunden fragen Agenturen jetzt aktiv nach Security. Ich bleibe Ihr zubuchbarer Partner. Kurzer Call?"),
    # Empfehlung
    _t("linkedin", "empfehlung", "Branchen-Referenz",
       "{{anrede}} {{name}}, ich durfte kürzlich einen {{branche}}-Betrieb absichern — ähnliche Einfallstore wie vermutlich bei {{firma}}. Wollen wir in 15 Minuten schauen, ob das für Sie relevant ist?"),
    _t("linkedin", "empfehlung", "Über Empfehler",
       "{{anrede}} {{name}}, [Empfehler] meinte, ich soll mich melden — ich habe dort die IT-Sicherheit auf einen prüfbaren Stand gebracht. Denselben Einstieg biete ich {{firma}}: kostenloser 15-Min-Quick-Check.",
       notes="[Empfehler] ersetzen."),
    _t("linkedin", "empfehlung", "Agentur-Referenz",
       "{{anrede}} {{name}}, für eine Agentur habe ich zuletzt die Kundenprojekte abgesichert und Ausschreibungs-Nachweise geliefert. Übertragbar auf {{firma}}? 15 Minuten dazu?"),
    # Angebot nachfassen
    _t("linkedin", "angebot_nachfassen", "Prioritäten einordnen",
       "{{anrede}} {{name}}, kurz zu meinem Angebot: Die offenen Punkte ({{aufhaenger}}) sind genau die, die im Ernstfall den Betrieb treffen. Ich ordne die Prioritäten in 10 Minuten ein — dann entscheiden Sie fundiert."),
    _t("linkedin", "angebot_nachfassen", "Noch aktuell?",
       "{{anrede}} {{name}}, bleibt die Absicherung für {{firma}} ein Thema dieses Quartal? Falls Budget der Punkt ist: Es geht auch abgestuft. Kurzer Call?"),
    _t("linkedin", "angebot_nachfassen", "Letzter Anstoß",
       "{{anrede}} {{name}}, letzter Anstoß: Wenn Security bei {{firma}} gerade keine Prio hat, völlig ok — ich melde mich später. Falls doch, halten wir die 15 Minuten fest."),
    # Security-Upsell
    _t("linkedin", "security_upsell", "Läuft die Absicherung mit?",
       "{{anrede}} {{name}}, Ihre Website läuft — aber Updates, Monitoring und Backups laufen mit? Ich biete das als festes Paket (Wartung + Security + jährlicher Check), ein Ansprechpartner, planbare Kosten. 15 Minuten zum Skizzieren?"),
    _t("linkedin", "security_upsell", "Nach Go-Live planbar schützen",
       "{{anrede}} {{name}}, nach dem Go-Live veralten Abhängigkeiten, neue Lücken kommen. Als Ihr Entwickler sichere ich {{firma}} planbar ab — Monitoring, Updates, jährlicher Check. Sollen wir das Paket festzurren?"),
    _t("linkedin", "security_upsell", "Schlanker Retainer",
       "{{anrede}} {{name}}, wir arbeiten schon zusammen — lassen Sie uns Security nicht dem Zufall überlassen. Schlanker Retainer mit klarer Monatspauschale. Vorschlag in 15 Minuten?"),
    # Security-Audit
    _t("linkedin", "security_audit", "Kostenloser Quick-Check",
       "{{anrede}} {{name}}, als Einstieg: kostenloser Security-Quick-Check. In 15 Minuten nenne ich die drei dringlichsten Punkte für {{firma}} — konkret, kein Verkaufsgespräch. Wann passt es?"),
    _t("linkedin", "security_audit", "Strukturiertes Audit",
       "{{anrede}} {{name}}, wenn Kunden/Versicherer Nachweise wollen, hilft kein Bauchgefühl. Mein Audit prüft {{firma}} strukturiert — und ich behebe die Findings auf Wunsch gleich mit. Start: 15-Min-Quick-Check."),
    _t("linkedin", "security_audit", "NIS2-Nachweisfähigkeit",
       "{{anrede}} {{name}}, NIS2 zieht Anforderungen über die Lieferkette — auch zu {{firma}}. Ein dokumentiertes Audit macht Sie nachweisfähig. Einstieg: kostenloser 15-Min-Quick-Check."),

    # ---- KI-Automatisierung ----
    _t("linkedin", "ki_automatisierung", "Rechnungseingang",
       "{{anrede}} {{name}}, Betriebe wie {{firma}} verlieren oft 10–20 Std./Woche mit dem Abtippen von Rechnungen. Ich automatisiere das mit KI (Dokument rein → strukturierte Daten in {{zielsystem}}) — DSGVO-konform, weil ich zertifizierter DSB und Entwickler bin. Einstieg: Prozess-Audit zum Festpreis. 15 Minuten für eine Live-Demo?"),
    _t("linkedin", "ki_automatisierung", "E-Mail-Triage",
       "{{anrede}} {{name}}, wer sortiert bei {{firma}} den Posteingang? KI kann Mails erkennen, kategorisieren und in {{zielsystem}} routen — Sonderfälle bleiben beim Menschen. Als IHK-DSB baue ich das DSGVO-konform. Einstieg: Festpreis-Audit mit DSGVO-Check. Kurzer Call?"),
    _t("linkedin", "ki_automatisierung", "ROI-Winkel",
       "{{anrede}} {{name}}, manuelle Dateneingabe bei {{firma}} kostet real oft einen Mitarbeitertag pro Woche. Ich automatisiere sie mit KI — individuell, wartbar, DSGVO-konform (ich bin zertifizierter DSB + Dev). Prozess-Audit zum Festpreis als risikoarmer Start. 15 Minuten?"),
]


# --------------------------------------------------------------------------- #
#  TELEFON (Gesprächsleitfaden, ##-Abschnitte, kein Betreff/keine Signatur)
# --------------------------------------------------------------------------- #
_PHONE = [
    # Kaltakquise
    _t("phone", "kaltakquise", "Leitfaden KMU-Geschäftsführer",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer von celox.io aus Berlin. Ich sichere IT für {{branche}}-Betriebe ab und melde mich, weil gerade kleinere Betriebe zur Zielscheibe werden. Haben Sie zwei Minuten?

## Nutzenargument
Ich bin kein reiner Berater — ich prüfe die typischen Einfallstore und behebe sie selbst: Härtung, Backups, sichere Zugänge, nach ISO 27001 und BSI-Grundschutz. Für {{firma}} heißt das: ein Ansprechpartner, der Risiken findet und schließt.

## Einwandbehandlung
- „Wir sind zu klein, uns greift keiner an.“ → Angriffe laufen automatisiert, Größe schützt nicht — ein Vorfall kostet schnell mehr als ein Jahr Absicherung.
- „Wir haben eine IT-Firma, die das macht.“ → Die hält den Betrieb am Laufen; Security ist eine eigene Disziplin. Ich ergänze und arbeite mit Ihrer IT zusammen.
- „Keine Zeit / kein Budget.“ → Deshalb nur 15 Minuten und ein abgestufter Einstieg — nicht alles auf einmal.

## Abschluss
Ich schlage einen kostenlosen 15-Minuten-Security-Quick-Check vor: die drei dringlichsten Punkte für {{firma}}. Passt Ihnen Donnerstag oder eher nächste Woche? Falls Datenschutz auch ein Thema ist — ich bin IHK-zertifizierter DSB, das lässt sich als ein Paket denken.""",
       notes="Deckt die drei Kern-Einwände ab. Abschluss = Quick-Check-Termin + DSB als optionales Add-on."),
    _t("phone", "kaltakquise", "Leitfaden Agentur/IT-Dienstleister",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io Berlin. Sie bauen mit {{firma}} für Kunden — ich rufe an, weil Security-Nachweise in Projekten immer öfter verlangt werden. Kurz zwei Minuten?

## Nutzenargument
Ich bin Ihr zubuchbarer Security-Partner: Prüfung, Härtung, sichere Architektur — umgesetzt, nicht nur empfohlen. Ihre Entwickler und ich sprechen dieselbe Sprache, und Sie liefern Kunden den Nachweis (ISO 27001, NIS2).

## Einwandbehandlung
- „Das machen unsere Entwickler.“ → Ideal — dann ergänze ich die Security-Tiefe und den Nachweis, ohne Ihr Team zu ersetzen.
- „Unsere Kunden fragen das nicht.“ → Noch nicht flächendeckend, in Ausschreibungen aber zunehmend K.-o.-Kriterium. Wer es vorhält, gewinnt.

## Abschluss
Lassen Sie uns in 15 Minuten ein aktuelles Projekt durchgehen — ich zeige, wo ich entlaste. Donnerstag oder Freitag? Datenschutz-Nachweise kann ich als DSB gleich mitliefern.""",
       notes="White-Label-Framing. DSB als Cross-Sell am Ende."),
    _t("phone", "kaltakquise", "Leitfaden Branchen-Risiko",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer von celox.io. In {{branche}} bedeutet {{risiko_branche}} sofort Umsatzausfall — deshalb der Anruf. Zwei Minuten?

## Nutzenargument
Ich prüfe gezielt, was bei {{firma}} den Betrieb lahmlegen könnte, und schließe die Lücken selbst — aus einer Hand, dokumentiert nach BSI-Grundschutz. Kein Bericht zum Ablegen, sondern echte Absicherung.

## Einwandbehandlung
- „Unsere Cyber-Versicherung deckt das ab.“ → Nur, wenn Sie die Mindeststandards belegen können — sonst wird gekürzt oder gar nicht gezahlt. Genau die belege ich.
- „Bisher ist nichts passiert.“ → Das ist Glück, keine Strategie. Die häufigsten Vorfälle treffen Betriebe ohne jede Vorbereitung.

## Abschluss
Kostenloser 15-Minuten-Quick-Check — die drei dringlichsten Punkte für {{firma}}. Wann passt es Ihnen? Auf Wunsch inkl. Datenschutz als ein Paket.""",
       notes="Versicherungs-Einwand fundiert entkräftet."),
    # Follow-up
    _t("phone", "followup", "Leitfaden Nachfass mit Mehrwert",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io — kurzer Nachfass zu unserem Austausch. Passt es gerade für zwei Minuten?

## Nutzenargument
Nicht mit leeren Händen: Der schnellste Schutz ist 2FA auf E-Mail und Buchhaltung — stoppt die häufigste Angriffsform, kostet nichts. Die weiteren Quick-Wins für {{firma}} gehe ich gern mit Ihnen durch.

## Einwandbehandlung
- „Hatte noch keine Zeit.“ → Verständlich — deshalb reichen 15 Minuten für die Einordnung, den Rest planen wir danach.
- „Melde mich, wenn's akut wird.“ → Bei Security ist 'akut' meist schon der Schadensfall. Vorher ist es ein Bruchteil des Aufwands.

## Abschluss
Sagen wir 15 Minuten diese Woche — Donnerstag? Ich zeige die drei wirksamsten Schritte für {{firma}}.""",
       notes="Mehrwert statt „nur nachhaken“."),
    _t("phone", "followup", "Leitfaden Anlass/Meldung",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer. Ich melde mich, weil die aktuelle Ransomware-Welle genau {{branche}} trifft — passt kurz?

## Nutzenargument
Das Muster ist immer gleich: Angreifer nehmen die, bei denen es schnell geht. Ich schließe bei {{firma}} genau diese schnellen Wege — und behebe die Findings selbst.

## Einwandbehandlung
- „Uns trifft das nicht.“ → Die Opfer dachten das auch. Automatisierte Angriffe fragen nicht nach Größe.

## Abschluss
15-Minuten-Quick-Check, kostenlos — ich zeige Ihnen die Lage für {{firma}}. Wann passt es?"""),
    _t("phone", "followup", "Leitfaden Agentur-Nachfass",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Kurzer Nachfass zur Security-Partnerschaft für {{firma}}.

## Nutzenargument
In Ausschreibungen wird der Security-Nachweis zum K.-o.-Kriterium. Als zubuchbarer Partner liefere ich ihn prüfbar — und arbeite Ihren Entwicklern zu.

## Einwandbehandlung
- „Aktuell keine passende Ausschreibung.“ → Genau dann vorbereiten — der Nachweis braucht Vorlauf, im Pitch ist es zu spät.

## Abschluss
15 Minuten an einem konkreten Projekt — Donnerstag oder Freitag?"""),
    # Reaktivierung
    _t("phone", "reaktivierung", "Leitfaden NIS2-Anlass",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Wir hatten vor einer Weile Kontakt — ich melde mich, weil sich für {{branche}} einiges geändert hat. Kurz Zeit?

## Nutzenargument
NIS2 zieht Sicherheitsanforderungen über Lieferketten auch zu kleineren Betrieben, und Angriffe nehmen zu. Ich bringe {{firma}} auf einen prüfbaren Stand — prüfen und umsetzen aus einer Hand.

## Einwandbehandlung
- „NIS2 betrifft uns nicht.“ → Direkt vielleicht nicht — aber über Ihre Kunden als Lieferant sehr wohl. Der Nachweis wird durchgereicht.

## Abschluss
Holen wir die 15 Minuten nach, die letztes Mal untergingen? Kostenloser Quick-Check für {{firma}}."""),
    _t("phone", "reaktivierung", "Leitfaden Versicherungs-Standards",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer. Neuer Anlauf zu unserem Thema — die Ausgangslage hat sich geändert. Zwei Minuten?

## Nutzenargument
Cyber-Versicherer verlangen inzwischen belegte Mindeststandards. Ich sorge dafür, dass {{firma}} sie erfüllt und belegen kann — und behebe die Lücken selbst.

## Einwandbehandlung
- „Wir sind doch versichert.“ → Nur nützt die Police nichts, wenn die Standards fehlen — dann wird gekürzt. Genau das prüfe ich.

## Abschluss
15-Minuten-Quick-Check diese Woche? Ich zeige, wo {{firma}} steht."""),
    _t("phone", "reaktivierung", "Leitfaden Agentur-Reaktivierung",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Unser Austausch war eingeschlafen — lag am Timing. Passt kurz?

## Nutzenargument
Endkunden fragen Agenturen jetzt aktiv nach Security-Nachweisen. Ich bleibe Ihr zubuchbarer Partner dafür — Nachweis und Umsetzung.

## Einwandbehandlung
- „Machen wir intern.“ → Prima, ich ergänze nur die Security-Tiefe und den prüfbaren Nachweis.

## Abschluss
15 Minuten, um zu schauen, wo es gerade brennt — wann passt es Ihnen?"""),
    # Empfehlung
    _t("phone", "empfehlung", "Leitfaden Branchen-Referenz",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Ich habe zuletzt einen {{branche}}-Betrieb abgesichert und rufe an, weil {{firma}} ähnlich aufgestellt ist. Kurz Zeit?

## Nutzenargument
Dort habe ich die häufigsten Einfallstore geschlossen — von Fernzugängen bis Backups — und einen auditfähigen Zustand hergestellt, ohne den Betrieb auszubremsen.

## Einwandbehandlung
- „Woher kennen Sie uns?“ → Über die Branche, nicht über Interna — die Muster wiederholen sich, deshalb der gezielte Anruf.

## Abschluss
Kostenloser 15-Minuten-Quick-Check — schauen wir, ob dieselben Punkte bei {{firma}} zählen. Wann passt es?"""),
    _t("phone", "empfehlung", "Leitfaden über Empfehler",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer. [Empfehler] hat den Kontakt angeregt — ich habe dort die IT-Sicherheit auf einen prüfbaren Stand gebracht. Zwei Minuten?

## Nutzenargument
Denselben Einstieg biete ich {{firma}}: konkrete Findings statt Folien, und ich behebe sie auf Wunsch selbst.

## Einwandbehandlung
- „Gerade kein Thema.“ → Verständlich — der Quick-Check ist kostenlos und unverbindlich, Sie wissen danach, ob überhaupt Bedarf ist.

## Abschluss
15 Minuten diese Woche? Ich richte mich nach Ihnen.""",
       notes="[Empfehler] vor dem Anruf durch echten Namen ersetzen."),
    _t("phone", "empfehlung", "Leitfaden Agentur-Referenz",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Für eine Digitalagentur habe ich zuletzt die Kundenprojekte abgesichert — das lässt sich auf {{firma}} übertragen. Kurz Zeit?

## Nutzenargument
Ein Ansprechpartner, der entwickelt UND härtet, plus die Nachweise für Ausschreibungen. Das entlastet Ihr Team und stärkt den Pitch.

## Einwandbehandlung
- „Wir haben Security-Leute.“ → Super, ich ergänze punktuell und liefere den prüfbaren Nachweis, ohne jemanden zu ersetzen.

## Abschluss
15 Minuten an einem konkreten Projekt — Donnerstag oder Freitag?"""),
    # Angebot nachfassen
    _t("phone", "angebot_nachfassen", "Leitfaden Risiko benennen",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Kurz zu meinem Angebot für {{firma}} — passt es gerade?

## Nutzenargument
Die offenen Punkte, u. a. {{aufhaenger}}, sind genau die, die im Ernstfall den Betrieb treffen. Ich will nichts verkaufen, das nicht schützt — deshalb der ehrliche Hinweis.

## Einwandbehandlung
- „Noch in der Abwägung.“ → Verständlich — lassen Sie mich die Prioritäten in 10 Minuten einordnen, dann entscheiden Sie fundiert.
- „Zu teuer.“ → Es geht abgestuft; wir fangen mit dem Dringlichsten an — immer noch ein Bruchteil eines Vorfalls.

## Abschluss
Sollen wir die wichtigsten zwei Punkte vorziehen? Ich halte einen Slot frei — passt morgen?"""),
    _t("phone", "angebot_nachfassen", "Leitfaden aktuell halten",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer. Nur eine kurze Rückfrage zu meinem Angebot, damit ich richtig plane. Zwei Minuten?

## Nutzenargument
Ist die Absicherung für {{firma}} noch ein Thema für dieses Quartal? Falls ja, halte ich Kapazität frei; falls Budget der Punkt ist, zeige ich einen abgestuften Einstieg.

## Einwandbehandlung
- „Muss intern klären.“ → Klar — womit unterstütze ich Sie dabei, vielleicht mit einer kurzen Entscheidungsvorlage?

## Abschluss
Ich schicke Ihnen zwei Terminvorschläge — passt Anfang nächster Woche?"""),
    _t("phone", "angebot_nachfassen", "Leitfaden letztes Nachfassen",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io — letzter kurzer Anstoß zu meinem Angebot, dann lasse ich Ruhe.

## Nutzenargument
Wenn Security bei {{firma}} gerade keine Priorität hat, ist das völlig in Ordnung. Ich will nur nicht, dass es aus Versehen liegen bleibt.

## Einwandbehandlung
- „Melde mich selbst.“ → Gerne — soll ich das Angebot bis Monatsende offen halten?

## Abschluss
Ein kurzes Ja und wir halten die 15 Minuten fest. Andernfalls melde ich mich in ein paar Monaten wieder."""),
    # Security-Upsell
    _t("phone", "security_upsell", "Leitfaden Website-Kunde",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Ihre Website/Anwendung läuft — ich rufe an, weil der laufende Schutz oft fehlt. Kurz Zeit?

## Nutzenargument
Updates, Monitoring, Backups, ein jährlicher Check — ungepatchte Systeme sind das häufigste Einfallstor. Ich schnüre das als festes Paket mit planbarer Monatspauschale, ein Ansprechpartner.

## Einwandbehandlung
- „Läuft doch bisher.“ → Genau das ist das Risiko — ohne Updates wächst die Angriffsfläche still, bis es zu spät ist.
- „Zu teuer.“ → Günstiger als ein Ausfalltag — und Sie sparen sich Feuerwehreinsätze.

## Abschluss
Ich skizziere Ihnen den Retainer in 15 Minuten — auf Wunsch inkl. Datenschutz-Betreuung. Passt Donnerstag?"""),
    _t("phone", "security_upsell", "Leitfaden Entwicklungskunde",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer. Nach unserem Projekt-Go-Live ein kurzer Gedanke zur dauerhaften Absicherung. Zwei Minuten?

## Nutzenargument
Abhängigkeiten veralten, neue Lücken werden bekannt. Als Ihr Entwickler kenne ich das System — die Absicherung sitzt schneller: Monitoring, Updates, jährlicher Check.

## Einwandbehandlung
- „Machen wir bei Bedarf.“ → 'Bei Bedarf' ist meist der Schadensfall. Planbar ist er ein Bruchteil.

## Abschluss
Lassen Sie uns das Paket in 15 Minuten festzurren — ich schlage eine klare Pauschale vor."""),
    _t("phone", "security_upsell", "Leitfaden Bestandskunde allgemein",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Wir arbeiten schon zusammen — ich möchte Security nicht dem Zufall überlassen. Kurz Zeit?

## Nutzenargument
Ein schlanker Retainer deckt das Wichtigste ab: Überwachung, Updates, Reaktion im Ernstfall, jährliche Prüfung nach BSI-Grundschutz.

## Einwandbehandlung
- „Ist das nötig?“ → Für den laufenden Betrieb ja — es ist die günstigste Versicherung gegen den teuersten Fall.

## Abschluss
Ich mache Ihnen einen Vorschlag mit klarer Monatspauschale — 15 Minuten diese Woche?"""),
    # Security-Audit
    _t("phone", "security_audit", "Leitfaden Quick-Check anbieten",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Ich biete einen kostenlosen Security-Quick-Check für {{branche}}-Betriebe — deshalb der Anruf. Zwei Minuten?

## Nutzenargument
In 15 Minuten nenne ich die drei dringlichsten Punkte für {{firma}} — konkret, ohne Fachchinesisch. Kein Verkaufsgespräch, sondern eine klare Einordnung.

## Einwandbehandlung
- „Was kostet das?“ → Der Quick-Check nichts. Erst wenn Sie eine Umsetzung wollen, sprechen wir über Aufwand.
- „Wir sind zu klein.“ → Automatisierte Angriffe fragen nicht nach Größe — gerade Kleine sind ungeschützt.

## Abschluss
Wann passt Ihnen der Quick-Check — Donnerstag oder nächste Woche?"""),
    _t("phone", "security_audit", "Leitfaden strukturiertes Audit",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Wenn Kunden oder Versicherer Nachweise verlangen, hilft kein Bauchgefühl — dafür rufe ich an. Kurz Zeit?

## Nutzenargument
Mein Security-Audit prüft {{firma}} strukturiert nach BSI-Grundschutz-/ISO-27001-Logik — und ich liefere nicht nur den Bericht, sondern behebe die Findings auf Wunsch gleich mit.

## Einwandbehandlung
- „Haben wir schon mal geprüft.“ → Gut — dann aktualisieren wir den Stand; Lücken entstehen laufend neu.

## Abschluss
Starten wir mit dem kostenlosen 15-Minuten-Quick-Check, damit Sie den Umfang einschätzen? Wann passt es?"""),
    _t("phone", "security_audit", "Leitfaden NIS2/Lieferkette",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. NIS2 zieht Anforderungen über die Lieferkette — auch zu {{firma}}. Zwei Minuten dazu?

## Nutzenargument
Ein dokumentiertes Security-Audit macht Sie gegenüber Ihren Kunden nachweisfähig — und ich setze die nötige Härtung gleich mit um.

## Einwandbehandlung
- „Das verlangt noch keiner.“ → Zunehmend doch, und mit Vorlauf. Wer den Nachweis hat, gewinnt die Ausschreibung.

## Abschluss
Einstieg ist der kostenlose 15-Minuten-Quick-Check — wann passt es Ihnen? Datenschutz-Nachweise kann ich als DSB mitliefern."""),

    # ---- KI-Automatisierung (Einwände aus dem Pitch-Spickzettel) ----
    _t("phone", "ki_automatisierung", "Leitfaden Rechnungseingang",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer von celox.io. Ich automatisiere Dokumentenprozesse mit KI und rufe an, weil das Abtippen von Rechnungen bei Betrieben wie {{firma}} oft 10–20 Stunden pro Woche frisst. Zwei Minuten?

## Nutzenargument
Das Prinzip: Dokument rein, geprüfte strukturierte Daten in {{zielsystem}} raus — Sonderfälle landen zur Kontrolle bei einem Menschen. Individuell und wartbar, ohne Cloud-Zwang. Und weil ich zertifizierter DSB bin, ist die DSGVO-Frage von Anfang an gelöst.

## Einwandbehandlung
- „KI und Datenschutz — geht das überhaupt?“ → Genau deshalb bin ich der Richtige: zertifizierter DSB, ich baue DSGVO-konform und liefere die Dokumentation mit.
- „Wir haben schon einen IT-Dienstleister.“ → Ich ersetze niemanden — ich liefere die KI-Automatisierung als Spezialgewerk und arbeite mit ihm zusammen.
- „Zu teuer.“ → Die Frage ist, was der manuelle Prozess Sie jeden Monat kostet. Ich rechne den ROI in Euro vor.
- „Unsere Daten sollen nicht in die Cloud.“ → Verstehe ich — im Audit prüfen wir On-Premise- und EU-Hosting-Optionen, das ist Teil des DSGVO-Checks.

## Abschluss
Risikoarmer erster Schritt: ein Prozess-Audit mit DSGVO-Check zum Festpreis {{audit_preis}}, Ergebnis nach {{audit_dauer}}, keine Bindung. Passt Ihnen ein 15-Minuten-Call diese Woche für eine Live-Demo mit einer Ihrer Beispielrechnungen?""",
       notes="Deckt die 4 Kern-Einwände aus dem Pitch ab. {{zielsystem}}/{{audit_preis}}/{{audit_dauer}} vorab setzen."),
    _t("phone", "ki_automatisierung", "Leitfaden E-Mail-Triage",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer, celox.io. Ich rufe an, weil bei vielen Betrieben wie {{firma}} der gemeinsame Posteingang täglich Stunden Sortierarbeit kostet. Kurz zwei Minuten?

## Nutzenargument
KI erkennt eingehende Mails, kategorisiert sie und routet sie an die richtige Stelle oder in {{zielsystem}} — Unklares bleibt beim Menschen. DSGVO-konform gebaut, weil ich zertifizierter DSB und Entwickler bin.

## Einwandbehandlung
- „Wir müssen erst intern klären.“ → Genau dafür ist das Audit da: Festpreis, klares Ergebnis, keine Bindung — der risikofreie erste Schritt.
- „KI und Datenschutz?“ → Ich liefere die Compliance gleich mit, das ist mein Kerngeschäft.
- „Zu teuer.“ → Ich zeige Ihnen die ROI-Rechnung; meist ist der manuelle Prozess der teurere Posten.

## Abschluss
Sollen wir mit einem Prozess-Audit starten (Festpreis {{audit_preis}}, {{audit_dauer}})? 15 Minuten diese Woche für eine kurze Demo?"""),
    _t("phone", "ki_automatisierung", "Leitfaden ROI/allgemein",
       """## Einstieg
{{anrede}} {{name}}, Martin Pfeffer von celox.io. Kurze Frage: Wie viele Stunden pro Woche tippt Ihr Team bei {{firma}} Daten von Hand ab? Zwei Minuten?

## Nutzenargument
Genau da setze ich mit KI an — Dokumente automatisch erfassen, prüfen und in {{zielsystem}} übergeben. Individuell und wartbar, kein Low-Code-Baukasten. DSGVO-konform, da ich zertifizierter DSB bin.

## Einwandbehandlung
- „Unsere Daten sollen nicht in die Cloud.“ → Kein Problem — On-Premise und EU-Hosting prüfen wir im Audit, Teil des DSGVO-Checks.
- „Wir haben schon jemanden für IT.“ → Ich ergänze als Spezialgewerk KI-Automatisierung, ohne jemanden zu ersetzen.
- „Zu teuer.“ → Der manuelle Prozess kostet monatlich mehr — ich rechne es Ihnen in Euro vor.

## Abschluss
Einstieg ist ein Festpreis-Audit ({{audit_preis}}, {{audit_dauer}}) mit ROI-Liste. 15 Minuten diese Woche?"""),
]


def default_templates() -> list[dict]:
    """Alle Seed-Templates (E-Mail signiert), mit sort_order 0..n je (Kanal, Rubrik)."""
    out: list[dict] = []
    for t in _EMAIL:
        t = dict(t)
        t["body"] = t["body"] + _SIG
        out.append(t)
    out.extend(dict(t) for t in _LINKEDIN)
    out.extend(dict(t) for t in _PHONE)
    counters: dict[tuple, int] = {}
    for t in out:
        key = (t["channel"], t["category"])
        t["sort_order"] = counters.get(key, 0)
        counters[key] = t["sort_order"] + 1
    return out
