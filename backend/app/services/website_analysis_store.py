"""Persistenz einer Website-Analyse — EINE Stelle für Router und Worker.

Vorher lag das Schreiben (Versions-Datensatz + denormalisierte Lead-Felder) nur
im Router; der Auto-Analyse-Worker hätte es duplizieren müssen. Hier gebündelt,
damit ein neues Analysefeld nur an einer Stelle nachgezogen wird.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_website_analysis import LeadWebsiteAnalysis


def analysis_row(lead_id, result: dict) -> LeadWebsiteAnalysis:
    """Analyse-Ergebnis → (noch nicht hinzugefügter) Versions-Datensatz."""
    return LeadWebsiteAnalysis(
        lead_id=lead_id,
        analysis_version=result["analysis_version"],
        url=result["url"],
        overall_score=result["overall_score"],
        rating=result["rating"],
        has_critical=result["has_critical"],
        categories=result["categories"],
        findings=result["findings"],
        technologies=result["technologies"],
        recommendations=result["recommendations"],
        meta=result["meta"],
        ai_review=result.get("ai_review"),
        pagespeed=result.get("pagespeed"),
    )


def apply_summary(lead, result: dict) -> None:
    """Denormalisierte Zusammenfassung am Lead aktualisieren (Liste ohne Join)."""
    lead.web_score = result["overall_score"]
    lead.web_rating = result["rating"]
    lead.web_has_critical = result["has_critical"]
    lead.web_analyzed_at = datetime.now(timezone.utc)


async def persist_analysis(db: AsyncSession, lead, result: dict) -> LeadWebsiteAnalysis:
    """Neue Analyse-Version speichern + Lead-Zusammenfassung setzen."""
    row = analysis_row(lead.id, result)
    db.add(row)
    apply_summary(lead, result)
    await db.flush()
    await db.refresh(row)
    return row
