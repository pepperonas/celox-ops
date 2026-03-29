import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.email_template import EmailTemplate
from app.schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)

router = APIRouter(
    prefix="/api/email-templates",
    tags=["email-templates"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[EmailTemplateResponse])
async def list_templates(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[EmailTemplateResponse]:
    query = select(EmailTemplate).order_by(EmailTemplate.category, EmailTemplate.name)
    if category:
        query = query.where(EmailTemplate.category == category)
    result = await db.execute(query)
    return [EmailTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    return EmailTemplateResponse.model_validate(template)


@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    template = EmailTemplate(
        name=data.name,
        subject=data.subject,
        body=data.body,
        category=data.category,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return EmailTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.flush()
    await db.refresh(template)
    return EmailTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    await db.delete(template)


@router.post("/seed", response_model=list[EmailTemplateResponse])
async def seed_templates(
    db: AsyncSession = Depends(get_db),
) -> list[EmailTemplateResponse]:
    """Erstellt Standard-Vorlagen, falls keine existieren."""
    count_result = await db.execute(select(func.count()).select_from(EmailTemplate))
    count = count_result.scalar_one()
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Es existieren bereits {count} Vorlagen. Seed nur bei leerer Tabelle möglich.",
        )

    defaults = [
        EmailTemplate(
            name="Rechnung versenden",
            subject="Rechnung {nr} — {firma}",
            body=(
                "Sehr geehrte Damen und Herren,\n\n"
                "anbei erhalten Sie die Rechnung {nr} über {betrag}.\n\n"
                "Bitte überweisen Sie den Betrag innerhalb der angegebenen Zahlungsfrist.\n\n"
                "Bei Fragen stehen wir Ihnen gerne zur Verfügung.\n\n"
                "Mit freundlichen Grüßen"
            ),
            category="rechnung",
        ),
        EmailTemplate(
            name="Zahlungserinnerung",
            subject="Zahlungserinnerung — Rechnung {nr}",
            body=(
                "Sehr geehrte Damen und Herren,\n\n"
                "wir möchten Sie freundlich daran erinnern, dass die Rechnung {nr} über {betrag} "
                "noch nicht beglichen wurde.\n\n"
                "Sollte sich Ihre Zahlung mit diesem Schreiben überschneiden, betrachten Sie "
                "diese Erinnerung bitte als gegenstandslos.\n\n"
                "Mit freundlichen Grüßen"
            ),
            category="mahnung",
        ),
        EmailTemplate(
            name="1. Mahnung",
            subject="1. Mahnung — Rechnung {nr}",
            body=(
                "Sehr geehrte Damen und Herren,\n\n"
                "trotz unserer Zahlungserinnerung ist die Rechnung {nr} über {betrag} "
                "weiterhin offen.\n\n"
                "Wir bitten Sie, den offenen Betrag umgehend zu überweisen.\n\n"
                "Mit freundlichen Grüßen"
            ),
            category="mahnung",
        ),
        EmailTemplate(
            name="Angebot versenden",
            subject="Angebot für {kunde}",
            body=(
                "Sehr geehrte Damen und Herren,\n\n"
                "vielen Dank für Ihr Interesse. Anbei erhalten Sie unser Angebot.\n\n"
                "Wir würden uns freuen, Sie als Kunden begrüßen zu dürfen. "
                "Bei Fragen stehen wir Ihnen gerne zur Verfügung.\n\n"
                "Mit freundlichen Grüßen"
            ),
            category="angebot",
        ),
        EmailTemplate(
            name="Akquise Erstansprache",
            subject="Zusammenarbeit mit {firma}",
            body=(
                "Sehr geehrte Damen und Herren,\n\n"
                "mein Name ist Martin Pfeffer und ich bin Softwareentwickler bei celox.io.\n\n"
                "Ich habe mir Ihre Webpräsenz angesehen und sehe Potenzial für eine "
                "Zusammenarbeit im Bereich Softwareentwicklung und KI-Integration.\n\n"
                "Hätten Sie Interesse an einem kurzen Austausch?\n\n"
                "Mit freundlichen Grüßen"
            ),
            category="akquise",
        ),
    ]

    for t in defaults:
        db.add(t)
    await db.flush()

    result = await db.execute(
        select(EmailTemplate).order_by(EmailTemplate.category, EmailTemplate.name)
    )
    return [EmailTemplateResponse.model_validate(t) for t in result.scalars().all()]
