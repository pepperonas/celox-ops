"""Tests fuer services/email_html.text_to_html_email — DB-frei, rein."""
from app.services.email_html import text_to_html_email


class _L:
    """Minimal-Text-Container fuer Lesbarkeit der Assertions."""


def test_escapes_html_special_chars():
    html = text_to_html_email("Preis < 100 & > 50, Firma \"Acme\"")
    assert "&lt;" in html and "&gt;" in html and "&amp;" in html
    # Kein roher spitzer Klammer-Text aus dem Nutzertext (nur unsere Tags).
    assert "< 100" not in html
    assert "\"Acme\"" not in html  # escaped zu &quot; / &#x27;


def test_linkifies_url_in_new_paragraph():
    html = text_to_html_email("Mehr dazu: https://celox.io/security jetzt.")
    assert '<a href="https://celox.io/security"' in html
    assert 'text-decoration:underline' in html


def test_url_trailing_punctuation_stays_outside_link():
    html = text_to_html_email("Siehe https://celox.io.")
    assert '<a href="https://celox.io"' in html
    # Der Punkt darf nicht Teil des href sein.
    assert 'href="https://celox.io."' not in html


def test_linkifies_email_as_mailto():
    html = text_to_html_email("Kontakt: martin.pfeffer@celox.io")
    assert '<a href="mailto:martin.pfeffer@celox.io"' in html


def test_paragraphs_from_blank_lines_and_br_from_single_newline():
    html = text_to_html_email("Zeile eins\nZeile zwei\n\nNeuer Absatz")
    assert html.count("<p ") == 2
    assert "Zeile eins<br>Zeile zwei" in html


def test_signature_block_is_split_off():
    text = "Guten Tag,\n\nkurzer Text.\n\nViele Grüße\nMartin Pfeffer\nhttps://celox.io"
    html = text_to_html_email(text)
    # <hr> trennt den Signaturblock ab, der in gedaempftem Grau steht.
    assert "<hr" in html
    assert "#6b7280" in html
    # Die Signatur-URL ist verlinkt.
    assert '<a href="https://celox.io"' in html
    # Vor der Signatur nur EIN <hr>.
    assert html.count("<hr") == 1


def test_no_signature_still_renders_body():
    html = text_to_html_email("Nur ein kurzer Text ohne Grußformel.")
    assert "<hr" not in html
    assert "Nur ein kurzer Text" in html


def test_empty_input_is_safe():
    html = text_to_html_email("")
    assert html.startswith("<div") and html.endswith("</div>")


def test_output_is_wrapped_container():
    html = text_to_html_email("Hallo")
    assert "max-width:600px" in html
