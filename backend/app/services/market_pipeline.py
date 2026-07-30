"""Marktradar → Rainmaker: einen Katalogeintrag als Lead in die Pipeline übernehmen.

Zum Lead wird der **Hersteller**, nicht das Produkt: verkauft wird ihm entweder
eine Partnerschaft (Marktplatz-Listing) oder eine Aufsatzlösung für seine
Kundenbasis. Der Katalogeintrag liefert dafür das Briefing — KI-Idee, größter
Pain, Nutzenschätzung, Referenzverzeichnis.

Die Referenzfirmen desselben Herstellers sind ein zweiter, größerer Lead-Weg;
der braucht aber erst die gescrapten Firmenlisten und kommt später hier daneben.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_product import MarketProduct, MarketStatus
from app.models.rainmaker_lead import RainmakerLead, RainmakerLeadStatus, RainmakerPriority
from app.services.lead_dedup import norm_website

LEAD_SOURCE = "Marktradar"


def vendor_website(ref_url: str | None) -> str | None:
    """Herstellerseite aus der Referenz-URL: Schema + Host, ohne Pfad.

    Die Referenz-URL zeigt immer auf eine Unterseite der Herstellerdomain — der
    Origin ist damit die Firmenwebsite und zugleich der Dedup-Schlüssel gegen
    bereits vorhandene Leads.
    """
    if not (ref_url or "").strip():
        return None
    parts = urlsplit(ref_url.strip())
    if not parts.netloc:
        return None
    return f"{parts.scheme or 'https'}://{parts.netloc}"


def _priority_for(score: int) -> RainmakerPriority:
    if score >= 75:
        return RainmakerPriority.high
    if score >= 60:
        return RainmakerPriority.medium
    return RainmakerPriority.low


def briefing(p: MarketProduct) -> str:
    """Gesprächsvorbereitung aus den Katalogfeldern — was der Lead im Notizfeld braucht."""
    zeilen = [
        f"Aus dem Marktradar übernommen (Opportunity Score {p.score}, Priorität {p.prio}).",
        f"Produkt: {p.produkt} — {p.kategorie}.",
    ]
    if p.ki:
        zeilen.append(f"Aufhänger (KI-Idee): {p.ki[0]}")
    if p.pains:
        zeilen.append(f"Handarbeit heute: {p.pains[0]}")
    if p.nutzen:
        zeilen.append(f"Nutzen: {p.nutzen}")
    if p.nutzer:
        zeilen.append(f"Tägliche Nutzer: {', '.join(p.nutzer[:3])}")
    if p.zielgruppe:
        zeilen.append(f"Zielgruppe des Produkts: {p.zielgruppe}")
    if p.marketplace and p.mp_evidence:
        zeilen.append(f"Marktplatz/Partnerprogramm: {', '.join(p.mp_evidence)} — Listing statt Einzelvertrieb prüfen.")
    if p.reg:
        zeilen.append(f"Regulatorischer Anlass: {', '.join(p.reg)}")
    if p.self_compete:
        zeilen.append("ACHTUNG: Hersteller besetzt den Use Case selbst — nur mit Nische oder als Partner.")
    zeilen.append(f"Referenzverzeichnis ({p.ref_status}, ca. {p.refs} Einträge): {p.ref_url}")
    if p.kunden:
        zeilen.append(f"Kundenbasis laut Hersteller: {p.kunden}")
    return "\n".join(zeilen)


def lead_tags(p: MarketProduct) -> list[str]:
    from app.services.market_catalog import kat_short

    tags = ["Marktradar", kat_short(p.kategorie)]
    if p.marketplace:
        tags.append("Marktplatz")
    tags.extend(p.reg or [])
    # Reihenfolge erhalten, Dubletten raus
    seen, out = set(), []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


async def find_existing_lead(db: AsyncSession, website: str | None) -> RainmakerLead | None:
    """Bewusst nur über die Website: ein Katalogeintrag trägt weder E-Mail noch
    Ansprechpartner, die vollständige Dreifachprüfung liefe hier ins Leere."""
    w = norm_website(website)
    if not w:
        return None
    return (
        await db.execute(select(RainmakerLead).where(RainmakerLead.website_norm == w).limit(1))
    ).scalar_one_or_none()


async def to_pipeline(
    db: AsyncSession,
    product: MarketProduct,
    *,
    force: bool = False,
    priority: str | None = None,
    note: str | None = None,
) -> tuple[RainmakerLead, bool, str | None]:
    """Legt den Hersteller als Rainmaker-Lead an und verknüpft ihn mit dem Eintrag.

    Rückgabe: (Lead, neu_angelegt, duplikat_grund).
    Ein bereits vorhandener Lead auf derselben Website wird **verknüpft statt
    dupliziert** — ohne `force` gibt der Router das als 409 an die Oberfläche.
    """
    # Die angereicherte Website ist die geprüfte (die Seite hat geantwortet); die
    # Ableitung aus der Referenz-URL bleibt der Rückfall.
    website = product.website or vendor_website(product.ref_url)

    vorhanden = await find_existing_lead(db, website)
    if vorhanden is not None and not force:
        return vorhanden, False, "website"

    if vorhanden is not None:
        lead = vorhanden
        neu = False
        # Vorhandenen Lead nur ERGÄNZEN: Was dort steht, ist gepflegt oder aus einer
        # verlässlicheren Quelle — ein Seiten-Scrape darf das nicht verdrängen.
        for feld in ("email", "phone", "decision_maker", "employee_count"):
            if not getattr(lead, feld, None) and getattr(product, feld, None):
                setattr(lead, feld, getattr(product, feld))
        if product.email and not lead.email_status:
            lead.email_status = product.email_status
    else:
        lead = RainmakerLead(
            company=product.vendor,
            website=website,
            source=LEAD_SOURCE,
            status=RainmakerLeadStatus.new,
            priority=RainmakerPriority(priority) if priority else _priority_for(product.score),
            target=product.kategorie[:120],
            tags=lead_tags(product),
            notes=briefing(product) + (f"\n\n{note}" if note else ""),
            value_estimate=Decimal(0),
            # Angereicherte Kontaktdaten mitgeben — nur, was da ist (die Anreicherung
            # lässt im Zweifel leer, und ein leeres Feld ist hier ein gültiges
            # Ergebnis, kein Grund für einen Platzhalter).
            email=product.email,
            email_status=product.email_status,
            phone=product.phone,
            decision_maker=product.decision_maker,
            employee_count=product.employee_count,
        )
        db.add(lead)
        try:
            async with db.begin_nested():
                await db.flush()
            neu = True
        except IntegrityError:
            # Race gegen die partiellen Unique-Indizes: den Gewinner verknüpfen.
            lead = await find_existing_lead(db, website)
            if lead is None:
                raise
            neu = False

    product.rainmaker_lead_id = lead.id
    product.status = MarketStatus.in_pipeline
    product.pushed_at = datetime.now(UTC)
    return lead, neu, None
