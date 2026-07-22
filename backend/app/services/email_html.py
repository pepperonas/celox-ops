"""Plain-Text-Mailtext → gestyltes, seriöses HTML (für den Lead-Mailversand).

Rein + testbar. HTML-Escaping ist Pflicht (der Text kommt von KI/Nutzer →
XSS-Schutz im Mail-Client). URLs und E-Mail-Adressen werden verlinkt, der
Signaturblock (ab „Viele Grüße"/„Mit freundlichen Grüßen") wird dezent
abgesetzt. Kein externes Bild/Logo (Deliverability, keine Remote-Requests).
"""
import html
import re

_URL_RE = re.compile(r"(https?://[^\s<]+)")
_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_SIG_RE = re.compile(r"^(Viele Grüße|Mit freundlichen Grüßen|Beste Grüße)\b", re.M)

_LINK = 'style="color:#2563eb;text-decoration:underline"'


def _trim_punct(url: str) -> tuple[str, str]:
    m = re.search(r"[.,;:!?)\]]+$", url)
    return (url[: -len(m.group(0))], m.group(0)) if m else (url, "")


def _linkify(escaped: str) -> str:
    """Verlinkt URLs und E-Mails in bereits HTML-escaptem Text."""
    def url_sub(m: re.Match) -> str:
        href, trail = _trim_punct(m.group(1))
        return f'<a href="{href}" {_LINK}>{href}</a>{trail}'

    out = _URL_RE.sub(url_sub, escaped)
    # E-Mails nur außerhalb bereits gesetzter <a>-Tags — simpel: Mails stehen im
    # Signaturblock ohne umschließende URL, daher unkritisch.
    out = _EMAIL_RE.sub(lambda m: f'<a href="mailto:{m.group(1)}" {_LINK}>{m.group(1)}</a>', out)
    return out


def _paragraphs_html(text: str) -> str:
    """Leerzeilen → Absätze, einfacher Umbruch → <br>."""
    blocks = re.split(r"\n\s*\n", text.strip())
    parts = []
    for block in blocks:
        inner = _linkify(html.escape(block)).replace("\n", "<br>")
        parts.append(f'<p style="margin:0 0 14px 0">{inner}</p>')
    return "\n".join(parts)


def text_to_html_email(text: str) -> str:
    """Baut das komplette HTML-Dokument der Mail. Signaturblock (falls erkannt)
    wird per <hr> abgesetzt und kleiner/gedämpft gesetzt."""
    text = (text or "").strip()
    sig_match = _SIG_RE.search(text)
    if sig_match:
        body_text = text[: sig_match.start()].rstrip()
        sig_text = text[sig_match.start():].strip()
    else:
        body_text, sig_text = text, ""

    body_html = _paragraphs_html(body_text) if body_text else ""

    sig_html = ""
    if sig_text:
        sig_inner = _linkify(html.escape(sig_text)).replace("\n", "<br>")
        sig_html = (
            '<hr style="border:none;border-top:1px solid #e5e7eb;margin:22px 0 14px 0">'
            f'<div style="font-size:13px;line-height:1.5;color:#6b7280">{sig_inner}</div>'
        )

    return (
        '<div style="margin:0;padding:0;background:#f6f7f9">'
        '<div style="max-width:600px;margin:0 auto;padding:28px 24px;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;'
        'font-size:15px;line-height:1.6;color:#1f2937;background:#ffffff">'
        f"{body_html}{sig_html}"
        "</div></div>"
    )
