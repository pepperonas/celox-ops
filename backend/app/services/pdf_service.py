import base64
import os
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.config import settings
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order


def _fetch_github_commits(customer: Customer, invoice: Invoice) -> list[dict] | None:
    """Fetch GitHub commits for the invoice period from customer's repos."""
    if not invoice.token_usage_from or not invoice.token_usage_to:
        return None
    if not customer.github_repos or not settings.GITHUB_TOKEN:
        return None

    import json
    repos = []
    try:
        parsed = json.loads(customer.github_repos)
        repos = parsed if isinstance(parsed, list) else [customer.github_repos]
    except (json.JSONDecodeError, TypeError):
        repos = [r.strip() for r in customer.github_repos.split(",") if r.strip()]

    if not repos:
        return None

    all_commits = []
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    for repo in repos:
        repo = repo.strip().strip("/")
        try:
            url = f"https://api.github.com/repos/{repo}/commits"
            params = {
                "since": f"{invoice.token_usage_from.isoformat()}T00:00:00Z",
                "until": f"{invoice.token_usage_to.isoformat()}T23:59:59Z",
                "per_page": 100,
            }
            resp = httpx.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                for c in resp.json():
                    all_commits.append({
                        "repo": repo.split("/")[-1] if "/" in repo else repo,
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].split("\n")[0][:120],
                        "author": c["commit"]["author"]["name"],
                        "date": c["commit"]["author"]["date"][:10],
                    })
        except Exception:
            continue

    return all_commits if all_commits else None


def _fetch_token_usage(customer: Customer, invoice: Invoice) -> dict | None:
    """Fetch token usage data from tracker if invoice has date range and customer has tracker URL."""
    if not invoice.token_usage_from or not invoice.token_usage_to:
        return None
    if not customer.token_tracker_url:
        return None

    try:
        params = {
            "from": invoice.token_usage_from.isoformat(),
            "to": invoice.token_usage_to.isoformat(),
        }
        sep = "&" if "?" in customer.token_tracker_url else "?"
        url = f"{customer.token_tracker_url}{sep}" + "&".join(f"{k}={v}" for k, v in params.items())
        resp = httpx.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def generate_invoice_pdf(
    invoice: Invoice,
    customer: Customer,
) -> str:
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("invoice.html")

    positions = invoice.positions or []

    token_usage = _fetch_token_usage(customer, invoice)
    github_commits = _fetch_github_commits(customer, invoice)

    # Load signature as base64
    signature_b64 = None
    sig_path = settings.SIGNATURE_PATH
    if sig_path and os.path.isfile(sig_path):
        with open(sig_path, "rb") as f:
            signature_b64 = base64.b64encode(f.read()).decode("utf-8")

    html_content = template.render(
        invoice=invoice,
        customer=customer,
        positions=positions,
        settings=settings,
        kleinunternehmer=settings.KLEINUNTERNEHMER,
        token_usage=token_usage,
        github_commits=github_commits,
        signature_b64=signature_b64,
    )

    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    filename = f"{invoice.invoice_number}.pdf"
    pdf_path = os.path.join(settings.PDF_STORAGE_PATH, filename)

    HTML(string=html_content).write_pdf(pdf_path)

    return pdf_path


def generate_quote_pdf(
    order: Order,
    customer: Customer,
) -> str:
    from datetime import date as date_type

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("quote.html")

    positions = order.positions or []
    subtotal = sum(float(p.get("gesamt", 0)) for p in positions) if positions else 0

    # Load signature as base64
    signature_b64 = None
    sig_path = settings.SIGNATURE_PATH
    if sig_path and os.path.isfile(sig_path):
        with open(sig_path, "rb") as f:
            signature_b64 = base64.b64encode(f.read()).decode("utf-8")

    quote_number = f"ANG-{order.title}"

    html_content = template.render(
        order=order,
        customer=customer,
        positions=positions,
        subtotal=subtotal,
        quote_number=quote_number,
        settings=settings,
        kleinunternehmer=settings.KLEINUNTERNEHMER,
        today=date_type.today(),
        signature_b64=signature_b64,
    )

    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    filename = f"Angebot-{order.title}.pdf"
    pdf_path = os.path.join(settings.PDF_STORAGE_PATH, filename)

    HTML(string=html_content).write_pdf(pdf_path)

    return pdf_path


def generate_reminder_pdf(
    invoice: Invoice,
    customer: Customer,
    level: int,
) -> str:
    from datetime import date as date_type

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("reminder.html")

    # Load signature as base64
    signature_b64 = None
    sig_path = settings.SIGNATURE_PATH
    if sig_path and os.path.isfile(sig_path):
        with open(sig_path, "rb") as f:
            signature_b64 = base64.b64encode(f.read()).decode("utf-8")

    html_content = template.render(
        invoice=invoice,
        customer=customer,
        level=level,
        settings=settings,
        today=date_type.today(),
        signature_b64=signature_b64,
    )

    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    level_names = {1: "Zahlungserinnerung", 2: "1-Mahnung", 3: "Letzte-Mahnung"}
    level_name = level_names.get(level, "Mahnung")
    filename = f"{level_name}_{invoice.invoice_number}.pdf"
    pdf_path = os.path.join(settings.PDF_STORAGE_PATH, filename)

    HTML(string=html_content).write_pdf(pdf_path)

    return pdf_path
