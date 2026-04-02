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
    date_from = invoice.github_commits_from or invoice.token_usage_from
    date_to = invoice.github_commits_to or invoice.token_usage_to
    if not date_from or not date_to:
        return None
    if not settings.GITHUB_TOKEN:
        return None

    import json
    # Use invoice-specific selection, fallback to all customer repos
    repos_source = invoice.selected_github_repos or customer.github_repos
    if not repos_source:
        return None
    repos = []
    try:
        parsed = json.loads(repos_source)
        repos = parsed if isinstance(parsed, list) else [repos_source]
    except (json.JSONDecodeError, TypeError):
        repos = [r.strip() for r in repos_source.split(",") if r.strip()]

    if not repos:
        return None

    all_commits = []
    daily_stats: dict[str, dict] = {}  # date -> {additions, deletions}
    total_additions = 0
    total_deletions = 0
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    for repo in repos:
        repo = repo.strip().strip("/")
        try:
            url = f"https://api.github.com/repos/{repo}/commits"
            params = {
                "since": f"{date_from.isoformat()}T00:00:00Z",
                "until": f"{date_to.isoformat()}T23:59:59Z",
                "per_page": 100,
            }
            resp = httpx.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                for c in resp.json():
                    sha = c["sha"]
                    date_str = c["commit"]["author"]["date"][:10]
                    additions = 0
                    deletions = 0
                    # Fetch individual commit for stats
                    try:
                        detail = httpx.get(
                            f"https://api.github.com/repos/{repo}/commits/{sha}",
                            headers=headers, timeout=10,
                        )
                        if detail.status_code == 200:
                            stats = detail.json().get("stats", {})
                            additions = stats.get("additions", 0)
                            deletions = stats.get("deletions", 0)
                    except Exception:
                        pass

                    total_additions += additions
                    total_deletions += deletions

                    if date_str not in daily_stats:
                        daily_stats[date_str] = {"additions": 0, "deletions": 0, "commits": 0}
                    daily_stats[date_str]["additions"] += additions
                    daily_stats[date_str]["deletions"] += deletions
                    daily_stats[date_str]["commits"] += 1

                    all_commits.append({
                        "repo": repo.split("/")[-1] if "/" in repo else repo,
                        "sha": sha[:7],
                        "message": c["commit"]["message"].split("\n")[0][:120],
                        "author": c["commit"]["author"]["name"],
                        "date": date_str,
                        "additions": additions,
                        "deletions": deletions,
                    })
        except Exception:
            continue

    if not all_commits:
        return None

    # Build daily chart data
    max_changes = max((d["additions"] + d["deletions"] for d in daily_stats.values()), default=1) or 1
    daily_chart = []
    for date_str in sorted(daily_stats.keys()):
        d = daily_stats[date_str]
        daily_chart.append({
            "date": date_str,
            "additions": d["additions"],
            "deletions": d["deletions"],
            "commits": d["commits"],
            "add_pct": round(d["additions"] / max_changes * 100),
            "del_pct": round(d["deletions"] / max_changes * 100),
        })

    return {
        "commits": all_commits,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "total_commits": len(all_commits),
        "daily_chart": daily_chart,
    }


def _fetch_token_usage(customer: Customer, invoice: Invoice) -> dict | None:
    """Fetch token usage data from tracker if invoice has date range and customer has tracker URL."""
    if not invoice.token_usage_from or not invoice.token_usage_to:
        return None

    import json as _json

    # Use invoice-specific selection, fallback to all customer URLs
    tracker_source = invoice.selected_tracker_urls or customer.token_tracker_url
    if not tracker_source:
        return None

    # Parse URLs from JSON (supports single URL, array of strings, array of {url, label} objects)
    urls: list[str] = []
    try:
        parsed = _json.loads(tracker_source)
        if isinstance(parsed, list):
            for item in parsed:
                urls.append(item["url"] if isinstance(item, dict) else item)
        else:
            urls = [tracker_source]
    except (_json.JSONDecodeError, TypeError):
        urls = [tracker_source]

    if not urls:
        return None

    # Fetch and merge all URLs
    merged = None
    for tracker_url in urls:
        try:
            params = {
                "from": invoice.token_usage_from.isoformat(),
                "to": invoice.token_usage_to.isoformat(),
            }
            sep = "&" if "?" in tracker_url else "?"
            url = f"{tracker_url}{sep}" + "&".join(f"{k}={v}" for k, v in params.items())
            resp = httpx.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if merged is None:
                    merged = data
                else:
                    # Merge summaries
                    for key in ["total_messages", "total_sessions", "total_cost", "lines_added", "lines_removed", "lines_written", "total_input_tokens", "total_output_tokens"]:
                        if key in merged.get("summary", {}) and key in data.get("summary", {}):
                            merged["summary"][key] += data["summary"][key]
                    merged["sessions"] = merged.get("sessions", []) + data.get("sessions", [])
                    merged["daily"] = merged.get("daily", []) + data.get("daily", [])
        except Exception:
            continue
    return merged


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

    # Prepare activity chart data from token_usage daily data
    activity_chart_data = None
    if invoice.include_activity_chart and token_usage and token_usage.get("daily"):
        from datetime import date as date_type, timedelta
        daily = token_usage["daily"]
        daily_map = {d["date"]: d for d in daily}

        # Build complete date range with all days
        if invoice.token_usage_from and invoice.token_usage_to:
            start = invoice.token_usage_from
            end = invoice.token_usage_to
            max_msgs = max((d.get("messages", 0) for d in daily), default=1) or 1
            chart = []
            current = start
            day_count = 0
            while current <= end:
                key = current.isoformat()
                d = daily_map.get(key, {})
                msgs = d.get("messages", 0)
                day_count += 1
                chart.append({
                    "date": key,
                    "messages": msgs,
                    "pct": round(msgs / max_msgs * 100) if msgs > 0 else 0,
                    "is_weekend": current.weekday() >= 5,
                    "label": current.strftime("%d.%m."),
                    "show_label": day_count % max(1, ((end - start).days + 1) // 15) == 0,
                })
                current += timedelta(days=1)
            activity_chart_data = chart

    # Calculate discount amount for template
    from decimal import Decimal as Dec
    positions_subtotal = sum(Dec(str(p.get("menge", 0))) * Dec(str(p.get("einzelpreis", 0))) for p in positions)
    discount_amount = Dec("0")
    if invoice.discount_type and invoice.discount_value:
        if invoice.discount_type == "percent":
            discount_amount = positions_subtotal * Dec(str(invoice.discount_value)) / Dec("100")
        else:
            discount_amount = Dec(str(invoice.discount_value))

    html_content = template.render(
        invoice=invoice,
        customer=customer,
        positions=positions,
        positions_subtotal=float(positions_subtotal),
        discount_amount=float(discount_amount),
        settings=settings,
        kleinunternehmer=settings.KLEINUNTERNEHMER,
        token_usage=token_usage,
        github_commits=github_commits,
        activity_chart_data=activity_chart_data,
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
