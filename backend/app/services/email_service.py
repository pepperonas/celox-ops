import asyncio
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import settings


def _send_email_sync(
    to_email: str,
    subject: str,
    body_html: str,
    pdf_path: str | None,
    cc: list[str] | None,
    bcc: list[str] | None,
) -> bool:
    """Blocking SMTP send — always call via asyncio.to_thread (an SMTP handshake
    can take seconds and would stall the single-worker event loop)."""
    cc_list = [c.strip() for c in (cc or []) if c and c.strip()]
    bcc_list = [b.strip() for b in (bcc or []) if b and b.strip()]

    msg = MIMEMultipart()
    msg["From"] = (
        f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        if settings.SMTP_FROM_NAME
        else settings.SMTP_FROM_EMAIL
    )
    msg["To"] = to_email
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html", "utf-8"))

    if pdf_path:
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF-Datei nicht gefunden: {pdf_path}")
        with open(path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=path.name,
            )
            msg.attach(attachment)

    recipients = [to_email] + cc_list + bcc_list

    # Port 465 uses implicit SSL; other ports (587, 25) use STARTTLS or plain
    use_ssl = settings.SMTP_PORT == 465
    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

    with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        if not use_ssl and settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(
            settings.SMTP_FROM_EMAIL,
            recipients,
            msg.as_string(),
        )

    return True


async def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    pdf_path: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> bool:
    """Send an email with optional PDF attachment via SMTP.

    Returns True on success. Raises on failure.
    Raises if SMTP_HOST is not configured.
    The blocking SMTP I/O runs in a worker thread (same pattern as WeasyPrint).
    """
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP ist nicht konfiguriert. Bitte SMTP_HOST in .env setzen.")

    return await asyncio.to_thread(
        _send_email_sync, to_email, subject, body_html, pdf_path, cc, bcc
    )
