import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import settings


async def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    pdf_path: str | None = None,
) -> bool:
    """Send an email with optional PDF attachment via SMTP.

    Returns True on success. Raises on failure.
    Skips silently (returns False) if SMTP_HOST is not configured.
    """
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP ist nicht konfiguriert. Bitte SMTP_HOST in .env setzen.")

    msg = MIMEMultipart()
    msg["From"] = (
        f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        if settings.SMTP_FROM_NAME
        else settings.SMTP_FROM_EMAIL
    )
    msg["To"] = to_email
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

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(
            settings.SMTP_FROM_EMAIL,
            [to_email],
            msg.as_string(),
        )

    return True
