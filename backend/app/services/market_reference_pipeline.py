"""Referenzkunde → Rainmaker-Lead: „Sie nutzen X, ich baue Y darauf."

**Das ist der Verkaufswinkel des ganzen Marktradars.** Eine Firma im
Referenzverzeichnis eines Herstellers nutzt dessen Software nachweislich — der
Hersteller sagt es selbst. Damit ist der Einstieg kein Kaltstart, sondern eine
Feststellung: „Sie arbeiten mit [Software], ich baue [Baustein] darauf." Genau das
Muster von bcsbook (Baustein 10, Zeiterfassungs-Assistent, auf Projektron BCS).

Unterschied zur Hersteller-Übergabe (`market_pipeline.py`): Dort wird dem Hersteller
eine Partnerschaft verkauft, hier dem Anwender eine Aufsatzlösung. Beide Wege
existieren nebeneinander; dieser ist der größere.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_baustein import MarketBaustein
from app.models.market_product import MarketProduct
from app.models.market_reference import MarketReference, norm_company
from app.models.rainmaker_lead import RainmakerLead, RainmakerLeadStatus, RainmakerPriority
from app.services.lead_dedup import norm_website

LEAD_SOURCE = "Marktradar-Referenz"


def bausteine_fuer(catalog_id: str, bausteine: list[MarketBaustein]) -> list[MarketBaustein]:
    """Welche Lösungsbausteine passen auf dieses Produkt? Rein.

    Die Zuordnung steht im Recherchekatalog (`market_bausteine.catalog_ids`) und wird
    hier nur gelesen — eine zweite Bewertung an dieser Stelle würde zwangsläufig von
    der Recherche abweichen.
    """
    return [b for b in bausteine if catalog_id in (b.catalog_ids or [])]


def briefing(
    reference: MarketReference, product: MarketProduct, bausteine: list[MarketBaustein],
) -> str:
    """Was im Notizfeld des Leads stehen muss, damit man das Gespräch führen kann.

    Reihenfolge nach Nutzen im Gespräch: erst der Anknüpfungspunkt (welche Software,
    woher wir das wissen), dann das Angebot (welcher Baustein), dann der Kontext.
    """
    zeilen = [
        f"Nutzt {product.produkt} ({product.hersteller}) — laut dessen "
        f"öffentlichem Referenzverzeichnis.",
        f"Beleg: {reference.source_url}",
    ]
    passend = bausteine_fuer(product.catalog_id, bausteine)
    if passend:
        zeilen.append("")
        zeilen.append("Aufsatzlösung, die hier passt:")
        for b in passend[:3]:
            was = (b.was or "").strip()
            zeilen.append(f"· Baustein {b.nr}: {b.titel}" + (f" — {was[:160]}" if was else ""))
    if product.pains:
        zeilen.append("")
        zeilen.append(f"Handarbeit in diesem Umfeld heute: {product.pains[0]}")
    if product.ki:
        zeilen.append(f"Aufhänger (KI-Idee): {product.ki[0]}")
    if product.kategorie:
        zeilen.append(f"Kategorie: {product.kategorie}")
    if not reference.website:
        # Ehrlich benennen, was fehlt — sonst sucht man im Lead nach einem Feld, das
        # nie gefüllt war. Logo-Wände liefern den Namen, aber keine Adresse.
        zeilen.append("")
        zeilen.append("Website unbekannt (aus einer Logo-Wand geerntet) — vor der "
                      "Ansprache heraussuchen.")
    return "\n".join(zeilen)


def lead_tags(product: MarketProduct) -> list[str]:
    from app.services.market_catalog import kat_short

    tags = ["Marktradar", "Referenzkunde", kat_short(product.kategorie)]
    gesehen, out = set(), []
    for t in tags:
        if t and t not in gesehen:
            gesehen.add(t)
            out.append(t)
    return out


async def find_existing_lead(
    db: AsyncSession, company: str, website: str | None,
) -> RainmakerLead | None:
    """Vorhandenen Lead finden — Website zuerst, dann der normalisierte Firmenname.

    **Anders als bei der Hersteller-Übergabe ist der Name hier ein Schlüssel.** Dort
    war er bewusst keiner (im Bestand stehen 22 Leads „Selbstständig"), aber ein
    Referenzkunde trägt einen echten Firmennamen und meist KEINE Website — ohne
    Namensprüfung entstünde bei jedem Lauf eine Dublette.
    """
    w = norm_website(website)
    if w:
        treffer = (await db.execute(
            select(RainmakerLead).where(RainmakerLead.website_norm == w).limit(1)
        )).scalar_one_or_none()
        if treffer is not None:
            return treffer
    schluessel = norm_company(company)
    if not schluessel:
        return None
    # Kein normalisiertes Namensfeld am Lead — deshalb Kandidaten grob vorfiltern und
    # in Python vergleichen. Bei einem Einzel-Push ist das billig.
    kandidaten = (await db.execute(
        select(RainmakerLead).where(RainmakerLead.company.ilike(f"%{company[:40]}%")).limit(50)
    )).scalars()
    for k in kandidaten:
        if norm_company(k.company) == schluessel:
            return k
    return None


async def reference_to_pipeline(
    db: AsyncSession,
    reference: MarketReference,
    product: MarketProduct,
    bausteine: list[MarketBaustein],
    *,
    force: bool = False,
) -> tuple[RainmakerLead, bool, str | None]:
    """Referenzkunde als Lead anlegen und mit dem Fund verknüpfen.

    Rückgabe: (Lead, neu_angelegt, duplikat_grund). Ein vorhandener Lead wird
    **verknüpft und ergänzt**, nie dupliziert; ohne `force` meldet der Router das als
    Rückfrage an die Oberfläche.
    """
    vorhanden = await find_existing_lead(db, reference.company, reference.website)
    if vorhanden is not None and not force:
        return vorhanden, False, "website" if reference.website else "name"

    text = briefing(reference, product, bausteine)
    if vorhanden is not None:
        lead = vorhanden
        neu = False
        # Nur ergänzen: Gepflegtes darf ein Fund aus einer Logo-Wand nicht verdrängen.
        if not lead.website and reference.website:
            lead.website = reference.website
        if not lead.target:
            lead.target = product.produkt[:120]
        lead.notes = f"{(lead.notes or '').rstrip()}\n\n{text}".strip()
        for tag in lead_tags(product):
            if tag not in (lead.tags or []):
                lead.tags = [*(lead.tags or []), tag]
    else:
        lead = RainmakerLead(
            company=reference.company,
            website=reference.website,
            source=LEAD_SOURCE,
            status=RainmakerLeadStatus.new,
            # Priorität aus dem Score des Produkts: Wie gut die Gelegenheit ist, hängt
            # am Umfeld, nicht an der einzelnen Firma — mehr wissen wir hier nicht.
            priority=(RainmakerPriority.high if product.score >= 75
                      else RainmakerPriority.medium if product.score >= 60
                      else RainmakerPriority.low),
            target=product.produkt[:120],
            tags=lead_tags(product),
            notes=text,
            value_estimate=Decimal(0),
        )
        db.add(lead)
        try:
            async with db.begin_nested():
                await db.flush()
            neu = True
        except IntegrityError:
            lead = await find_existing_lead(db, reference.company, reference.website)
            if lead is None:
                raise
            neu = False

    reference.rainmaker_lead_id = lead.id
    reference.status = "in_pipeline"
    return lead, neu, None
