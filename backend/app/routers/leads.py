import math
import re
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.lead import Lead
from app.schemas.lead import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
)

router = APIRouter(
    prefix="/api/leads",
    tags=["leads"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_leads(
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Lead)
    count_query = select(func.count()).select_from(Lead)

    if search:
        search_filter = f"%{search}%"
        condition = (
            Lead.url.ilike(search_filter)
            | Lead.name.ilike(search_filter)
            | Lead.company.ilike(search_filter)
            | Lead.notes.ilike(search_filter)
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    if status_filter:
        query = query.where(Lead.status == status_filter)
        count_query = count_query.where(Lead.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Lead, sort_by, Lead.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "items": [LeadResponse.model_validate(l) for l in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    lead = Lead(**data.model_dump(exclude_unset=True))
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)

    await db.flush()
    await db.refresh(lead)
    return LeadResponse.model_validate(lead)


class AnalyzeRequest(BaseModel):
    url: str


class Finding(BaseModel):
    category: str
    issue: str
    severity: str  # critical, warning, info


class AnalyzeResponse(BaseModel):
    score: int  # 0-100
    findings: list[Finding]
    load_time_ms: int
    url: str


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_website(data: AnalyzeRequest) -> AnalyzeResponse:
    """Analysiert eine Website auf Qualitätsprobleme."""
    url = data.url.strip()
    if not url.startswith("http"):
        url = f"https://{url}"

    findings: list[Finding] = []
    score = 100
    load_time_ms = 0

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; celox-ops-analyzer/1.0)"})
        load_time_ms = int((time.time() - start) * 1000)
        html = resp.text.lower()
        headers = {k.lower(): v.lower() for k, v in resp.headers.items()}

        # --- SSL ---
        if not resp.url.scheme == "https":
            findings.append(Finding(category="Sicherheit", issue="Kein HTTPS — Website ist nicht verschlüsselt", severity="critical"))
            score -= 20
        elif data.url.startswith("http://"):
            # Check if HTTP redirects to HTTPS
            findings.append(Finding(category="Sicherheit", issue="HTTPS vorhanden, aber kein automatischer Redirect von HTTP", severity="warning"))
            score -= 5

        # --- Ladezeit ---
        if load_time_ms > 5000:
            findings.append(Finding(category="Performance", issue=f"Sehr langsam: {load_time_ms / 1000:.1f}s Ladezeit", severity="critical"))
            score -= 15
        elif load_time_ms > 3000:
            findings.append(Finding(category="Performance", issue=f"Langsam: {load_time_ms / 1000:.1f}s Ladezeit", severity="warning"))
            score -= 8
        elif load_time_ms > 1500:
            findings.append(Finding(category="Performance", issue=f"Akzeptable Ladezeit: {load_time_ms / 1000:.1f}s", severity="info"))
            score -= 3

        # --- Mobile / Responsive ---
        has_viewport = 'name="viewport"' in html or "name='viewport'" in html
        if not has_viewport:
            findings.append(Finding(category="Mobile", issue="Kein Viewport-Meta-Tag — Website ist nicht mobiloptimiert", severity="critical"))
            score -= 15

        # --- SEO ---
        has_title = "<title>" in html and "</title>" in html
        title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        title_text = title_match.group(1).strip() if title_match else ""

        if not has_title or not title_text:
            findings.append(Finding(category="SEO", issue="Kein <title>-Tag — schlecht für Suchmaschinen", severity="critical"))
            score -= 10
        elif len(title_text) < 10:
            findings.append(Finding(category="SEO", issue=f"Titel zu kurz ({len(title_text)} Zeichen) — wenig aussagekräftig", severity="warning"))
            score -= 5

        has_description = 'name="description"' in html or "name='description'" in html
        if not has_description:
            findings.append(Finding(category="SEO", issue="Keine Meta-Description — Suchmaschinen zeigen keinen Beschreibungstext", severity="warning"))
            score -= 8

        has_h1 = "<h1" in html
        if not has_h1:
            findings.append(Finding(category="SEO", issue="Keine H1-Überschrift — Seitenstruktur fehlt", severity="warning"))
            score -= 5

        # --- Bilder ---
        img_count = html.count("<img")
        img_no_alt = len(re.findall(r'<img(?![^>]*alt=)[^>]*>', html))
        if img_count > 0 and img_no_alt > 0:
            pct = int(img_no_alt / img_count * 100)
            findings.append(Finding(category="Barrierefreiheit", issue=f"{img_no_alt} von {img_count} Bildern ohne Alt-Text ({pct}%)", severity="warning"))
            score -= min(10, img_no_alt * 2)

        # --- Technologie ---
        if "jquery" in html and ("jquery-1." in html or "jquery-2." in html or "jquery.min.js" in html):
            findings.append(Finding(category="Technologie", issue="jQuery erkannt — möglicherweise veralteter Technologie-Stack", severity="info"))
            score -= 3

        if "wp-content" in html:
            findings.append(Finding(category="Technologie", issue="WordPress erkannt", severity="info"))
            # Check for outdated WP signs
            if "flavor" in html or "flavour" in html:
                pass  # neutral
            generator_match = re.search(r'name="generator"[^>]*content="wordpress\s*([\d.]+)', html)
            if generator_match:
                wp_version = generator_match.group(1)
                findings.append(Finding(category="Sicherheit", issue=f"WordPress-Version {wp_version} öffentlich sichtbar", severity="warning"))
                score -= 5

        # --- Seitengröße ---
        content_length = len(resp.content)
        if content_length > 2_000_000:
            findings.append(Finding(category="Performance", issue=f"Sehr große Seite: {content_length / 1_000_000:.1f} MB", severity="warning"))
            score -= 5
        elif content_length > 500_000:
            findings.append(Finding(category="Performance", issue=f"Große Seite: {content_length / 1000:.0f} KB", severity="info"))
            score -= 2

        # --- Fehlende Security-Header ---
        if "content-security-policy" not in headers:
            findings.append(Finding(category="Sicherheit", issue="Kein Content-Security-Policy Header", severity="info"))
            score -= 2
        if "x-frame-options" not in headers:
            findings.append(Finding(category="Sicherheit", issue="Kein X-Frame-Options Header — Clickjacking möglich", severity="info"))
            score -= 2

        # --- Keine Findings = gut ---
        if not findings:
            findings.append(Finding(category="Allgemein", issue="Keine offensichtlichen Probleme gefunden", severity="info"))

    except httpx.ConnectError:
        findings.append(Finding(category="Erreichbarkeit", issue="Website nicht erreichbar — Verbindung fehlgeschlagen", severity="critical"))
        score = 0
    except httpx.TimeoutException:
        findings.append(Finding(category="Erreichbarkeit", issue="Website-Timeout nach 15 Sekunden", severity="critical"))
        score = 10
    except Exception as e:
        findings.append(Finding(category="Fehler", issue=f"Analyse fehlgeschlagen: {str(e)[:100]}", severity="critical"))
        score = 0

    return AnalyzeResponse(
        score=max(0, min(100, score)),
        findings=findings,
        load_time_ms=load_time_ms,
        url=url,
    )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    await db.delete(lead)
