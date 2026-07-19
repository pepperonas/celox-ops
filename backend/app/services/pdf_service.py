import base64
import concurrent.futures
import os
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.config import settings
from app.services.filenames import download_name
from app.services.address_format import format_address_lines
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order

# Commit line stats are immutable → cache across PDF regenerations / refresh-drafts.
_commit_stats_cache: dict[tuple[str, str], tuple[int, int]] = {}


def _fetch_commit_stats_bulk(
    pairs: list[tuple[str, str]], headers: dict
) -> dict[tuple[str, str], tuple[int, int]]:
    """Fetch (additions, deletions) for each (repo, sha) concurrently, cached.
    Replaces the old sequential one-request-per-commit N+1."""
    todo = [p for p in set(pairs) if p not in _commit_stats_cache]

    def _one(pair: tuple[str, str]) -> None:
        repo, sha = pair
        add = dele = 0
        try:
            r = httpx.get(
                f"https://api.github.com/repos/{repo}/commits/{sha}",
                headers=headers, timeout=8,
            )
            if r.status_code == 200:
                st = r.json().get("stats", {})
                add, dele = st.get("additions", 0), st.get("deletions", 0)
        except Exception:
            pass
        _commit_stats_cache[pair] = (add, dele)

    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(_one, todo))
    return {p: _commit_stats_cache.get(p, (0, 0)) for p in pairs}


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

    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Pass 1: list commits (one call per repo — no per-commit detail yet).
    listed: list[dict] = []
    for repo in repos:
        repo = repo.strip().strip("/")
        try:
            resp = httpx.get(
                f"https://api.github.com/repos/{repo}/commits",
                headers=headers,
                params={
                    "since": f"{date_from.isoformat()}T00:00:00Z",
                    "until": f"{date_to.isoformat()}T23:59:59Z",
                    "per_page": 100,
                },
                timeout=8,
            )
            if resp.status_code == 200:
                for c in resp.json():
                    listed.append({
                        "repo_full": repo,
                        "repo": repo.split("/")[-1] if "/" in repo else repo,
                        "sha_full": c["sha"],
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].split("\n")[0][:120],
                        "author": c["commit"]["author"]["name"],
                        "date": c["commit"]["author"]["date"][:10],
                    })
        except Exception:
            continue

    if not listed:
        return None

    # Pass 2: fetch per-commit line stats CONCURRENTLY (bounded), cached by (repo, sha)
    # since commit stats are immutable. Avoids the old N+1 (one 8s call per commit).
    stats_map = _fetch_commit_stats_bulk([(c["repo_full"], c["sha_full"]) for c in listed], headers)

    all_commits = []
    daily_stats: dict[str, dict] = {}
    total_additions = 0
    total_deletions = 0
    for c in listed:
        additions, deletions = stats_map.get((c["repo_full"], c["sha_full"]), (0, 0))
        total_additions += additions
        total_deletions += deletions
        d = daily_stats.setdefault(c["date"], {"additions": 0, "deletions": 0, "commits": 0})
        d["additions"] += additions
        d["deletions"] += deletions
        d["commits"] += 1
        all_commits.append({
            "repo": c["repo"], "sha": c["sha"], "message": c["message"],
            "author": c["author"], "date": c["date"],
            "additions": additions, "deletions": deletions,
        })

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
            resp = httpx.get(url, timeout=8)
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
    env.filters["address_lines"] = format_address_lines
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
        from datetime import timedelta
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

    # Parse special terms (JSON array or plain string)
    import json as _json2
    special_terms_list = []
    if invoice.special_terms:
        try:
            parsed = _json2.loads(invoice.special_terms)
            special_terms_list = [t for t in parsed if t.strip()] if isinstance(parsed, list) else [invoice.special_terms]
        except (_json2.JSONDecodeError, TypeError):
            special_terms_list = [invoice.special_terms]

    # Optional logo as base64
    logo_b64 = None
    if settings.LOGO_PATH and os.path.isfile(settings.LOGO_PATH):
        with open(settings.LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Optional payment link (replace {amount} + {invoice_number})
    payment_link = None
    payment_qr_b64 = None
    if settings.PAYMENT_LINK_TEMPLATE:
        payment_link = (
            settings.PAYMENT_LINK_TEMPLATE
            .replace("{amount}", f"{float(invoice.total):.2f}")
            .replace("{invoice_number}", invoice.invoice_number)
        )
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(payment_link)
            qr.make(fit=True)
            img = qr.make_image()
            buf = BytesIO()
            img.save(buf, format="PNG")
            payment_qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass

    html_content = template.render(
        invoice=invoice,
        customer=customer,
        positions=positions,
        positions_subtotal=float(positions_subtotal),
        discount_amount=float(discount_amount),
        special_terms_list=special_terms_list,
        settings=settings,
        kleinunternehmer=settings.KLEINUNTERNEHMER,
        token_usage=token_usage,
        github_commits=github_commits,
        activity_chart_data=activity_chart_data,
        signature_b64=signature_b64,
        logo_b64=logo_b64,
        payment_link=payment_link,
        payment_qr_b64=payment_qr_b64,
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
    env.filters["address_lines"] = format_address_lines
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

    # Speichername slug-sicher: ein "/" im Auftragstitel würde sonst den
    # os.path.join-Pfad brechen. Der Download-Name kommt aus routers/orders.py.
    filename = download_name("Angebot", order.title)
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
    env.filters["address_lines"] = format_address_lines
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
