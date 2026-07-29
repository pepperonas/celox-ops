"""Die E-Mail-Signatur des Absenders — EINE Quelle für alle ausgehenden Texte.

Vorher stand sie zweimal im Code: als feste Signatur unter den KI-Entwürfen
(`lead_email_ai`) und, in einer kürzeren Fassung, unter den Akquise-Vorlagen
(`outreach_seed`). Damit trugen zwei Mails vom selben Absender zwei
verschiedene Signaturen — und eine Adress- oder Telefonänderung hätte an einer
Stelle vergessen werden können.

Bewusst ein eigenes Modul und nicht in `lead_email_ai`: Die Vorlagen haben mit
KI nichts zu tun; ein Import von dort würde den ganzen Anthropic-Stack in ein
Modul ziehen, das reiner Text ist.

Nicht zu verwechseln mit `settings.SIGNATURE_PATH` — das ist das eingescannte
Unterschriftsbild für PDFs.
"""

# Reine Text-Fassung (Zwischenablage, Plain-Text-Teil einer Mail). Die
# HTML-Fassung entsteht daraus in `email_html.text_to_html_email`, das den Block
# ab „Viele Grüße" erkennt und per <hr> absetzt — die erste Zeile ist deshalb
# nicht beliebig.
SIGNATURE = (
    "Viele Grüße\n"
    "Martin Pfeffer\n\n"
    "celox.io — Softwareentwicklung, IT-Sicherheit & Datenschutz\n"
    "Datenschutzbeauftragter (IHK) · IT-Sicherheitsbeauftragter (ISO 27001)\n\n"
    "Flughafenstraße 24, 12053 Berlin\n"
    "+49 151 590 824 65 · martin.pfeffer@celox.io\n"
    "https://celox.io"
)

# Die Signatur, die die Akquise-Vorlagen bis 2026-07-29 trugen. Bleibt hier
# stehen, damit `scripts/update_outreach_signature.py` sie in bestehenden
# Vorlagen exakt erkennen und ersetzen kann — ein Muster-Match („alles ab dem
# ersten Grußwort") würde eigene Nachsätze des Nutzers mitlöschen.
LEGACY_TEMPLATE_SIGNATURE = "Beste Grüße\nMartin Pfeffer\ncelox.io · Berlin"
