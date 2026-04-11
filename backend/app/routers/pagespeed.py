import json
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from jinja2 import Template
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.pagespeed_result import PagespeedResult
from app.schemas.pagespeed_result import PagespeedResultResponse

router = APIRouter(
    prefix="/api/pagespeed",
    tags=["pagespeed"],
    dependencies=[Depends(get_current_user)],
)

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

PDF_DIR = "/data/pagespeed"

REPORT_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><style>
@page { size: A4; margin: 2cm 2.5cm 3cm 2.5cm; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; line-height: 1.5; }
h1 { font-size: 16pt; color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }
h2 { font-size: 12pt; color: #1a1a2e; margin-top: 20px; }
.score-grid { display: flex; gap: 15px; margin: 20px 0; }
.score-box { flex: 1; text-align: center; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
.score-value { font-size: 28pt; font-weight: bold; }
.score-label { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.5px; color: #666; margin-top: 4px; }
.green { color: #0cce6b; border-color: #0cce6b40; background: #0cce6b08; }
.orange { color: #ffa400; border-color: #ffa40040; background: #ffa40008; }
.red { color: #ff4e42; border-color: #ff4e4240; background: #ff4e4208; }
.metric-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
.metric-table th { text-align: left; font-size: 9pt; color: #666; border-bottom: 1px solid #e0e0e0; padding: 6px 8px; }
.metric-table td { padding: 6px 8px; font-size: 9pt; border-bottom: 1px solid #f0f0f0; }
.metric-table tr:hover td { background: #f8f8f8; }
.opportunity { padding: 8px 10px; margin: 5px 0; background: #fff8e1; border-left: 3px solid #ffa400; border-radius: 0 4px 4px 0; font-size: 9pt; }
.diagnostic { padding: 8px 10px; margin: 5px 0; background: #fce4ec; border-left: 3px solid #ff4e42; border-radius: 0 4px 4px 0; font-size: 9pt; }
.passed { padding: 6px 10px; margin: 3px 0; font-size: 9pt; color: #666; }
.passed::before { content: "\\2713 "; color: #0cce6b; }
.meta { font-size: 8pt; color: #999; margin-top: 20px; }
</style></head><body>
<h1>Google PageSpeed Insights Report</h1>
<p><strong>URL:</strong> {{ url }}<br>
<strong>Strategie:</strong> {{ strategy }}<br>
<strong>Datum:</strong> {{ datum }}</p>

<div class="score-grid">
{% for cat in categories %}
<div class="score-box {{ cat.color }}">
    <div class="score-value">{{ cat.score }}</div>
    <div class="score-label">{{ cat.label }}</div>
</div>
{% endfor %}
</div>

<h2>Core Web Vitals & Metriken</h2>
<table class="metric-table">
<thead><tr><th>Metrik</th><th>Wert</th><th>Bewertung</th></tr></thead>
<tbody>
{% for m in metrics %}
<tr>
    <td><strong>{{ m.label }}</strong></td>
    <td>{{ m.value }}</td>
    <td style="color: {{ m.color }}">{{ m.rating }}</td>
</tr>
{% endfor %}
</tbody>
</table>

{% if opportunities %}
<h2>Optimierungsm\u00f6glichkeiten</h2>
{% for o in opportunities %}
<div class="opportunity">
    <strong>{{ o.title }}</strong>
    {% if o.savings %}<span style="float: right; color: #ffa400;">{{ o.savings }}</span>{% endif %}
    {% if o.description %}<br><span style="color: #666;">{{ o.description }}</span>{% endif %}
</div>
{% endfor %}
{% endif %}

{% if diagnostics %}
<h2>Diagnose</h2>
{% for d in diagnostics %}
<div class="diagnostic">
    <strong>{{ d.title }}</strong>
    {% if d.description %}<br><span style="color: #666;">{{ d.description }}</span>{% endif %}
</div>
{% endfor %}
{% endif %}

{% if passed %}
<h2>Bestanden ({{ passed|length }})</h2>
{% for p in passed %}
<div class="passed">{{ p }}</div>
{% endfor %}
{% endif %}

<p class="meta">Generiert via Google PageSpeed Insights API v5. Daten k\u00f6nnen je nach Netzwerk und Serverauslastung variieren.</p>
</body></html>""")


def _score_color(score: float) -> str:
    if score >= 0.9:
        return "green"
    elif score >= 0.5:
        return "orange"
    return "red"


def _score_label(score: float) -> str:
    if score >= 0.9:
        return "Gut"
    elif score >= 0.5:
        return "Verbesserungsbedarf"
    return "Schlecht"


def _color_hex(score: float) -> str:
    if score >= 0.9:
        return "#0cce6b"
    elif score >= 0.5:
        return "#ffa400"
    return "#ff4e42"


@router.get("/analyze")
async def analyze_pagespeed(
    url: str = Query(...),
    strategy: str = Query("mobile", regex="^(mobile|desktop)$"),
    customer_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Führt Google PageSpeed Analyse durch, speichert Ergebnis und gibt PDF zurück."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            params: dict = {
                "url": url,
                "strategy": strategy,
                "category": ["performance", "accessibility", "best-practices", "seo"],
            }
            if settings.PAGESPEED_API_KEY:
                params["key"] = settings.PAGESPEED_API_KEY
            resp = await client.get(PAGESPEED_API, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"PageSpeed API Fehler: {resp.status_code}")
        data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="PageSpeed API Timeout (60s)")

    lhr = data.get("lighthouseResult", {})
    cats = lhr.get("categories", {})
    audits = lhr.get("audits", {})

    # Categories
    categories = []
    cat_map = {
        "performance": "Performance",
        "accessibility": "Barrierefreiheit",
        "best-practices": "Best Practices",
        "seo": "SEO",
    }
    score_values = {}
    for key, label in cat_map.items():
        cat = cats.get(key, {})
        score = cat.get("score", 0) or 0
        score_values[key] = int(score * 100)
        categories.append({
            "label": label,
            "score": score_values[key],
            "color": _score_color(score),
        })

    # Core Web Vitals
    metrics = []
    metric_map = {
        "first-contentful-paint": "First Contentful Paint",
        "largest-contentful-paint": "Largest Contentful Paint",
        "total-blocking-time": "Total Blocking Time",
        "cumulative-layout-shift": "Cumulative Layout Shift",
        "speed-index": "Speed Index",
        "interactive": "Time to Interactive",
    }
    for key, label in metric_map.items():
        audit = audits.get(key, {})
        score = audit.get("score", 0) or 0
        metrics.append({
            "label": label,
            "value": audit.get("displayValue", "\u2013"),
            "rating": _score_label(score),
            "color": _color_hex(score),
        })

    # Opportunities
    opportunities = []
    for key, audit in audits.items():
        if audit.get("details", {}).get("type") == "opportunity" and audit.get("score", 1) < 0.9:
            savings = audit.get("details", {}).get("overallSavingsMs")
            opportunities.append({
                "title": audit.get("title", key),
                "description": audit.get("description", "")[:200],
                "savings": f"{int(savings)}ms" if savings else None,
            })
    opportunities.sort(key=lambda x: int((x.get("savings") or "0ms").replace("ms", "") or 0), reverse=True)

    # Diagnostics
    diagnostics = []
    for key, audit in audits.items():
        if audit.get("details", {}).get("type") == "table" and audit.get("score", 1) is not None and audit.get("score", 1) < 0.5:
            diagnostics.append({
                "title": audit.get("title", key),
                "description": audit.get("description", "")[:200],
            })

    # Passed audits
    passed = [
        audit.get("title", key)
        for key, audit in audits.items()
        if audit.get("score") == 1 and audit.get("scoreDisplayMode") == "binary"
    ][:20]

    from datetime import date as date_type
    html = REPORT_TEMPLATE.render(
        url=url,
        strategy="Mobile" if strategy == "mobile" else "Desktop",
        datum=date_type.today().strftime("%d.%m.%Y"),
        categories=categories,
        metrics=metrics,
        opportunities=opportunities[:10],
        diagnostics=diagnostics[:10],
        passed=passed,
    )

    pdf = HTML(string=html).write_pdf()
    domain = url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    filename = f"PageSpeed_{domain}.pdf"

    # Save to DB if customer_id provided
    if customer_id:
        os.makedirs(PDF_DIR, exist_ok=True)
        result_id = uuid.uuid4()
        pdf_filename = f"{result_id}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf)

        result = PagespeedResult(
            id=result_id,
            customer_id=uuid.UUID(customer_id),
            url=url,
            strategy=strategy,
            score_performance=score_values.get("performance"),
            score_accessibility=score_values.get("accessibility"),
            score_best_practices=score_values.get("best-practices"),
            score_seo=score_values.get("seo"),
            pdf_path=pdf_path,
            raw_scores=json.dumps(score_values),
        )
        db.add(result)
        await db.commit()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/results", response_model=list[PagespeedResultResponse])
async def list_pagespeed_results(
    customer_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[PagespeedResultResponse]:
    """Liste aller PageSpeed-Ergebnisse für einen Kunden."""
    result = await db.execute(
        select(PagespeedResult)
        .where(PagespeedResult.customer_id == uuid.UUID(customer_id))
        .order_by(PagespeedResult.created_at.desc())
    )
    return [PagespeedResultResponse.model_validate(r) for r in result.scalars().all()]


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pagespeed_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Löscht ein PageSpeed-Ergebnis und die zugehörige PDF."""
    result = await db.execute(
        select(PagespeedResult).where(PagespeedResult.id == uuid.UUID(result_id))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Ergebnis nicht gefunden")

    # Delete PDF file
    if entry.pdf_path and os.path.exists(entry.pdf_path):
        os.remove(entry.pdf_path)

    await db.execute(
        delete(PagespeedResult).where(PagespeedResult.id == uuid.UUID(result_id))
    )
    await db.commit()


@router.get("/results/{result_id}/pdf")
async def download_pagespeed_pdf(
    result_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Lädt die gespeicherte PDF eines PageSpeed-Ergebnisses herunter."""
    result = await db.execute(
        select(PagespeedResult).where(PagespeedResult.id == uuid.UUID(result_id))
    )
    entry = result.scalar_one_or_none()
    if not entry or not entry.pdf_path:
        raise HTTPException(status_code=404, detail="PDF nicht gefunden")

    if not os.path.exists(entry.pdf_path):
        raise HTTPException(status_code=404, detail="PDF-Datei nicht gefunden")

    with open(entry.pdf_path, "rb") as f:
        pdf_data = f.read()

    domain = entry.url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
    filename = f"PageSpeed_{domain}_{entry.created_at.strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
