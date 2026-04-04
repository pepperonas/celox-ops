import math
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetail,
    InvoiceResponse,
    InvoiceStatusUpdate,
    InvoiceUpdate,
    PaymentRequest,
    QuickInvoiceCreate,
)
from pydantic import BaseModel as PydanticBaseModel

from app.models.activity import Activity
from app.services.email_service import send_email
from app.services.invoice_service import calculate_invoice_totals, generate_invoice_number
from app.services.pdf_service import generate_invoice_pdf, generate_reminder_pdf


class EmailRequest(PydanticBaseModel):
    to_email: str
    subject: str | None = None
    message: str | None = None

router = APIRouter(
    prefix="/api/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_invoices(
    customer_id: uuid.UUID | None = Query(None),
    invoice_status: InvoiceStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Invoice).options(joinedload(Invoice.customer))
    count_query = select(func.count()).select_from(Invoice)

    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
        count_query = count_query.where(Invoice.customer_id == customer_id)
    if invoice_status:
        query = query.where(Invoice.status == invoice_status)
        count_query = count_query.where(Invoice.status == invoice_status)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Invoice, sort_by, Invoice.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invoices = result.scalars().unique().all()

    responses = []
    for inv in invoices:
        resp = InvoiceResponse.model_validate(inv)
        resp.customer_name = inv.customer.name if inv.customer else ""
        responses.append(resp)

    return {
        "items": responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceDetail:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    detail = InvoiceDetail.model_validate(invoice)
    detail.customer_name = invoice.customer.name if invoice.customer else ""
    return detail


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    # Verify customer
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    invoice_number = await generate_invoice_number(db)

    positions_dicts = [p.model_dump() for p in data.positions]
    # Convert Decimal to str for JSON serialization
    positions_json = []
    for p in positions_dicts:
        positions_json.append({
            k: str(v) if hasattr(v, "quantize") else v
            for k, v in p.items()
        })

    subtotal, tax_amount, total = calculate_invoice_totals(
        positions_dicts, data.tax_rate, data.tax_exempt,
        discount_type=data.discount_type, discount_value=data.discount_value,
    )

    invoice = Invoice(
        customer_id=data.customer_id,
        order_id=data.order_id,
        contract_id=data.contract_id,
        invoice_number=invoice_number,
        title=data.title,
        positions=positions_json,
        subtotal=subtotal,
        tax_rate=data.tax_rate if not data.tax_exempt else Decimal("0"),
        tax_exempt=data.tax_exempt,
        tax_amount=tax_amount,
        total=total,
        invoice_date=data.invoice_date,
        due_date=data.due_date,
        notes=data.notes,
        discount_type=data.discount_type,
        discount_value=Decimal(str(data.discount_value)) if data.discount_value else None,
        discount_reason=data.discount_reason,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)

    activity = Activity(
        customer_id=data.customer_id,
        type="invoice",
        title=f"Rechnung {invoice_number} erstellt",
        description=f"{invoice.title} — {float(invoice.total):.2f} €",
    )
    db.add(activity)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = customer.name
    return resp


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)

    if "positions" in update_data and update_data["positions"] is not None:
        positions_dicts = [p.model_dump() for p in data.positions]  # type: ignore[union-attr]
        positions_json = []
        for p in positions_dicts:
            positions_json.append({
                k: str(v) if hasattr(v, "quantize") else v
                for k, v in p.items()
            })
        update_data["positions"] = positions_json

        tax_rate = data.tax_rate if data.tax_rate is not None else invoice.tax_rate
        tax_exempt = data.tax_exempt if data.tax_exempt is not None else invoice.tax_exempt
        d_type = data.discount_type if data.discount_type is not None else invoice.discount_type
        d_value = data.discount_value if data.discount_value is not None else (float(invoice.discount_value) if invoice.discount_value else None)
        subtotal, tax_amount, total = calculate_invoice_totals(
            positions_dicts, tax_rate, tax_exempt,
            discount_type=d_type, discount_value=d_value,
        )
        update_data["subtotal"] = subtotal
        update_data["tax_amount"] = tax_amount
        update_data["total"] = total

    for key, value in update_data.items():
        setattr(invoice, key, value)

    await db.flush()
    await db.refresh(invoice)

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one()

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.put("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: uuid.UUID,
    data: InvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    invoice.status = data.status
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.post("/{invoice_id}/generate-pdf", response_model=InvoiceResponse)
async def generate_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    pdf_path = generate_invoice_pdf(invoice, invoice.customer)
    invoice.pdf_path = pdf_path
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.get("/{invoice_id}/pdf")
async def download_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.pdf_path:
        raise HTTPException(status_code=404, detail="PDF wurde noch nicht generiert")

    return FileResponse(
        path=invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post("/{invoice_id}/remind", response_model=InvoiceResponse)
async def send_reminder(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Mahnstufe erhöhen und Mahnung versenden."""
    from datetime import date as date_type, datetime as dt_type, timezone

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    if invoice.status not in (InvoiceStatus.gestellt, InvoiceStatus.ueberfaellig):
        raise HTTPException(
            status_code=400,
            detail="Mahnungen können nur für gestellte oder überfällige Rechnungen erstellt werden",
        )

    if invoice.due_date >= date_type.today():
        raise HTTPException(
            status_code=400,
            detail="Rechnung ist noch nicht fällig",
        )

    if invoice.reminder_level >= 3:
        raise HTTPException(
            status_code=400,
            detail="Maximale Mahnstufe (3) bereits erreicht",
        )

    invoice.reminder_level += 1
    invoice.reminder_sent_at = dt_type.now(timezone.utc)

    if invoice.status == InvoiceStatus.gestellt:
        invoice.status = InvoiceStatus.ueberfaellig

    await db.flush()
    await db.refresh(invoice)

    activity = Activity(
        customer_id=invoice.customer_id,
        type="invoice",
        title=f"Mahnung gesendet: {invoice.invoice_number}",
        description=f"Mahnstufe {invoice.reminder_level} — {float(invoice.total):.2f} €",
    )
    db.add(activity)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.post("/{invoice_id}/generate-reminder-pdf", response_model=InvoiceResponse)
async def generate_reminder_pdf_endpoint(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Mahnungs-PDF generieren."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    if invoice.reminder_level < 1:
        raise HTTPException(
            status_code=400,
            detail="Keine Mahnung vorhanden. Bitte zuerst eine Mahnung senden.",
        )

    pdf_path = generate_reminder_pdf(invoice, invoice.customer, invoice.reminder_level)
    invoice.reminder_pdf_path = pdf_path
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.get("/{invoice_id}/reminder-pdf")
async def download_reminder_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Mahnungs-PDF herunterladen."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.reminder_pdf_path:
        raise HTTPException(status_code=404, detail="Mahnungs-PDF wurde noch nicht generiert")

    level_names = {1: "Zahlungserinnerung", 2: "1-Mahnung", 3: "Letzte-Mahnung"}
    level_name = level_names.get(invoice.reminder_level, "Mahnung")

    return FileResponse(
        path=invoice.reminder_pdf_path,
        media_type="application/pdf",
        filename=f"{level_name}_{invoice.invoice_number}.pdf",
    )


@router.post("/{invoice_id}/send-email")
async def send_invoice_email(
    invoice_id: uuid.UUID,
    data: EmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rechnung per E-Mail senden."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.pdf_path:
        raise HTTPException(status_code=400, detail="PDF wurde noch nicht generiert. Bitte zuerst PDF erstellen.")

    customer = invoice.customer

    subject = data.subject or f"Rechnung {invoice.invoice_number} — {settings.BUSINESS_NAME}"

    if data.message:
        body_html = data.message.replace("\n", "<br>")
    else:
        customer_name = customer.name if customer else "Kunde"
        body_html = (
            f"Sehr geehrte Damen und Herren,<br><br>"
            f"anbei erhalten Sie die Rechnung <strong>{invoice.invoice_number}</strong> "
            f"über <strong>{invoice.total:.2f} EUR</strong>.<br><br>"
            f"Bitte überweisen Sie den Betrag bis zum <strong>{invoice.due_date.strftime('%d.%m.%Y')}</strong> "
            f"auf folgendes Konto:<br>"
            f"IBAN: {settings.BUSINESS_BANK_IBAN}<br>"
            f"BIC: {settings.BUSINESS_BANK_BIC}<br>"
            f"Bank: {settings.BUSINESS_BANK_NAME}<br><br>"
            f"Bei Fragen stehen wir Ihnen gerne zur Verfügung.<br><br>"
            f"Mit freundlichen Grüßen<br>"
            f"{settings.BUSINESS_OWNER}<br>"
            f"{settings.BUSINESS_NAME}"
        )

    try:
        await send_email(
            to_email=data.to_email,
            subject=subject,
            body_html=body_html,
            pdf_path=invoice.pdf_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"E-Mail-Versand fehlgeschlagen: {e}")

    activity = Activity(
        customer_id=invoice.customer_id,
        type="email",
        title=f"Rechnung per E-Mail gesendet: {invoice.invoice_number}",
        description=f"An {data.to_email} — {float(invoice.total):.2f} €",
    )
    db.add(activity)

    return {"success": True, "message": f"Rechnung wurde an {data.to_email} gesendet."}


@router.post("/{invoice_id}/send-reminder-email")
async def send_reminder_email(
    invoice_id: uuid.UUID,
    data: EmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mahnung per E-Mail senden."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.reminder_pdf_path:
        raise HTTPException(status_code=400, detail="Mahnungs-PDF wurde noch nicht generiert.")
    if invoice.reminder_level < 1:
        raise HTTPException(status_code=400, detail="Keine Mahnung vorhanden.")

    level_names = {1: "Zahlungserinnerung", 2: "1. Mahnung", 3: "Letzte Mahnung"}
    level_name = level_names.get(invoice.reminder_level, "Mahnung")

    subject = data.subject or f"{level_name} — Rechnung {invoice.invoice_number} — {settings.BUSINESS_NAME}"

    if data.message:
        body_html = data.message.replace("\n", "<br>")
    else:
        body_html = (
            f"Sehr geehrte Damen und Herren,<br><br>"
            f"wir möchten Sie daran erinnern, dass die Rechnung "
            f"<strong>{invoice.invoice_number}</strong> über "
            f"<strong>{invoice.total:.2f} EUR</strong> noch offen ist.<br><br>"
            f"Die Fälligkeit war am <strong>{invoice.due_date.strftime('%d.%m.%Y')}</strong>. "
            f"Bitte überweisen Sie den offenen Betrag umgehend auf folgendes Konto:<br>"
            f"IBAN: {settings.BUSINESS_BANK_IBAN}<br>"
            f"BIC: {settings.BUSINESS_BANK_BIC}<br>"
            f"Bank: {settings.BUSINESS_BANK_NAME}<br><br>"
            f"Sollte sich Ihre Zahlung mit diesem Schreiben überschneiden, "
            f"betrachten Sie diese Erinnerung bitte als gegenstandslos.<br><br>"
            f"Mit freundlichen Grüßen<br>"
            f"{settings.BUSINESS_OWNER}<br>"
            f"{settings.BUSINESS_NAME}"
        )

    try:
        await send_email(
            to_email=data.to_email,
            subject=subject,
            body_html=body_html,
            pdf_path=invoice.reminder_pdf_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"E-Mail-Versand fehlgeschlagen: {e}")

    activity = Activity(
        customer_id=invoice.customer_id,
        type="email",
        title=f"{level_name} per E-Mail gesendet: {invoice.invoice_number}",
        description=f"An {data.to_email} — {float(invoice.total):.2f} €",
    )
    db.add(activity)

    return {"success": True, "message": f"{level_name} wurde an {data.to_email} gesendet."}


@router.post("/refresh-drafts")
async def refresh_drafts(db: AsyncSession = Depends(get_db)) -> dict:
    """Aktualisiert alle Entwürfe: token_usage_to + github_commits_to auf heute, reimportiert KI-Daten, regeneriert PDFs."""
    from datetime import date, timedelta
    import json
    import httpx

    today = date.today()

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.status == InvoiceStatus.entwurf)
    )
    drafts = result.scalars().unique().all()

    updated_count = 0
    pdf_count = 0

    for inv in drafts:
        changed = False

        # Update token_usage_to to today
        if inv.token_usage_from:
            inv.token_usage_to = today
            changed = True

            # Re-fetch KI data and rebuild positions
            customer = inv.customer
            tracker_source = inv.selected_tracker_urls or (customer.token_tracker_url if customer else None)
            if tracker_source:
                urls: list[str] = []
                try:
                    parsed = json.loads(tracker_source)
                    if isinstance(parsed, list):
                        for item in parsed:
                            urls.append(item if isinstance(item, str) else item.get("url", ""))
                    else:
                        urls = [tracker_source]
                except (json.JSONDecodeError, TypeError):
                    urls = [tracker_source]

                # Fetch token data from all URLs
                total_active_min = 0
                total_cost = 0.0
                total_sessions = 0
                total_lines = 0
                for url in urls:
                    try:
                        params = {"from": inv.token_usage_from.isoformat(), "to": today.isoformat()}
                        sep = "&" if "?" in url else "?"
                        full_url = f"{url}{sep}" + "&".join(f"{k}={v}" for k, v in params.items())
                        resp = httpx.get(full_url, timeout=30)
                        if resp.status_code == 200:
                            data = resp.json()
                            s = data.get("summary", {})
                            total_active_min += s.get("total_active_min", 0)
                            total_cost += s.get("total_cost", 0)
                            total_sessions += s.get("total_sessions", 0)
                            total_lines += s.get("lines_written", 0)
                    except Exception:
                        continue

                if total_active_min > 0:
                    hours = round(total_active_min / 60, 2)
                    # Find hourly rate from existing position or default to 95
                    hourly_rate = Decimal("95")
                    for p in (inv.positions or []):
                        if "Stunden" in str(p.get("einheit", "")) and float(p.get("einzelpreis", 0)) > 0:
                            hourly_rate = Decimal(str(p["einzelpreis"]))
                            break

                    period_from = inv.token_usage_from.isoformat()
                    period_to = today.isoformat()
                    cost_eur = round(total_cost * 0.92, 2)

                    new_positions = [{
                        "position": 1,
                        "beschreibung": f"{inv.title} ({period_from} – {period_to})",
                        "menge": str(hours),
                        "einheit": "Stunden",
                        "einzelpreis": str(hourly_rate),
                        "gesamt": str(round(hours * float(hourly_rate), 2)),
                    }]
                    if cost_eur > 0:
                        new_positions.append({
                            "position": 2,
                            "beschreibung": "Technische Infrastruktur & externe Systemkosten",
                            "menge": "1",
                            "einheit": "pauschal",
                            "einzelpreis": str(cost_eur),
                            "gesamt": str(cost_eur),
                        })

                    # Keep non-KI positions (manually added ones)
                    manual_positions = [p for p in (inv.positions or [])
                                       if not str(p.get("beschreibung", "")).startswith("KI-")]
                    all_positions = new_positions + manual_positions
                    for i, p in enumerate(all_positions):
                        p["position"] = i + 1

                    inv.positions = all_positions

                    # Recalculate totals
                    subtotal, tax_amount, total_amount = calculate_invoice_totals(
                        all_positions, inv.tax_rate, inv.tax_exempt,
                        discount_type=inv.discount_type,
                        discount_value=float(inv.discount_value) if inv.discount_value else None,
                    )
                    inv.subtotal = subtotal
                    inv.tax_amount = tax_amount
                    inv.total = total_amount

        # Update github_commits_to to today
        if inv.github_commits_from:
            inv.github_commits_to = today
            changed = True

        if changed:
            updated_count += 1
            # Regenerate PDF
            try:
                from app.services.pdf_service import generate_invoice_pdf
                pdf_path = generate_invoice_pdf(inv, inv.customer)
                inv.pdf_path = pdf_path
                pdf_count += 1
            except Exception:
                pass

    await db.flush()

    return {
        "updated": updated_count,
        "pdfs_generated": pdf_count,
        "total_drafts": len(drafts),
    }


@router.post("/generate-recurring", response_model=list[InvoiceResponse])
async def generate_recurring_invoices(db: AsyncSession = Depends(get_db)) -> list:
    """Erstellt Entwurfsrechnungen für fällige Vertragsabrechnungen."""
    from datetime import date as date_type, timedelta
    from decimal import Decimal

    from dateutil.relativedelta import relativedelta

    from app.models.contract import BillingCycle, Contract, ContractStatus

    today = date_type.today()

    # Get all active contracts
    result = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer))
        .where(Contract.status == ContractStatus.aktiv)
    )
    contracts = result.scalars().unique().all()

    if not contracts:
        return []

    cycle_months = {
        BillingCycle.monatlich: 1,
        BillingCycle.quartalsweise: 3,
        BillingCycle.halbjaehrlich: 6,
        BillingCycle.jaehrlich: 12,
    }

    german_months = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ]

    processed_contract_ids: set[uuid.UUID] = set()

    for contract in contracts:
        months = cycle_months[contract.billing_cycle]

        if contract.last_invoiced_date is None:
            # Never invoiced — due immediately
            is_due = True
        else:
            next_date = contract.last_invoiced_date + relativedelta(months=months)
            is_due = next_date <= today

        if not is_due:
            continue

        # Build period label
        if contract.billing_cycle == BillingCycle.monatlich:
            period_label = f"{german_months[today.month]} {today.year}"
        elif contract.billing_cycle == BillingCycle.quartalsweise:
            quarter = (today.month - 1) // 3 + 1
            period_label = f"Q{quarter} {today.year}"
        elif contract.billing_cycle == BillingCycle.halbjaehrlich:
            half = 1 if today.month <= 6 else 2
            period_label = f"{half}. Halbjahr {today.year}"
        else:  # jaehrlich
            period_label = str(today.year)

        # Calculate amount
        amount = contract.monthly_amount * Decimal(str(months))

        # Build invoice
        invoice_number = await generate_invoice_number(db)

        positions_json = [{
            "position": 1,
            "beschreibung": contract.title,
            "menge": "1",
            "einheit": period_label,
            "einzelpreis": str(amount),
            "gesamt": str(amount),
        }]

        positions_dicts = [{
            "position": 1,
            "beschreibung": contract.title,
            "menge": Decimal("1"),
            "einheit": period_label,
            "einzelpreis": amount,
            "gesamt": amount,
        }]

        is_exempt = settings.KLEINUNTERNEHMER
        subtotal, tax_amount, total = calculate_invoice_totals(
            positions_dicts, Decimal("19.00"), is_exempt
        )

        invoice = Invoice(
            customer_id=contract.customer_id,
            contract_id=contract.id,
            invoice_number=invoice_number,
            title=f"{contract.title} — {period_label}",
            positions=positions_json,
            subtotal=subtotal,
            tax_rate=Decimal("0") if is_exempt else Decimal("19.00"),
            tax_exempt=is_exempt,
            tax_amount=tax_amount,
            total=total,
            invoice_date=today,
            due_date=today + timedelta(days=14),
            status=InvoiceStatus.entwurf,
        )
        db.add(invoice)

        # Update contract
        contract.last_invoiced_date = today
        processed_contract_ids.add(contract.id)

    if not processed_contract_ids:
        return []

    await db.flush()

    # Re-query the invoices we just created to get customer data
    new_result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(
            Invoice.status == InvoiceStatus.entwurf,
            Invoice.invoice_date == today,
            Invoice.contract_id.in_(processed_contract_ids),
        )
        .order_by(Invoice.created_at.desc())
    )
    new_invoices = new_result.scalars().unique().all()

    responses = []
    for inv in new_invoices:
        resp = InvoiceResponse.model_validate(inv)
        resp.customer_name = inv.customer.name if inv.customer else ""
        responses.append(resp)

    return responses


@router.post("/quick", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def quick_invoice(
    data: QuickInvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Schnellrechnung: Eine Position, keine Auftrags-/Vertragsverknüpfung."""
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    invoice_number = await generate_invoice_number(db)

    from datetime import date, timedelta
    from decimal import Decimal

    gesamt = data.menge * data.einzelpreis
    positions_json = [{
        "position": 1,
        "beschreibung": data.beschreibung,
        "menge": str(data.menge),
        "einheit": data.einheit,
        "einzelpreis": str(data.einzelpreis),
        "gesamt": str(gesamt),
    }]

    subtotal = gesamt
    is_exempt = settings.KLEINUNTERNEHMER
    if is_exempt:
        tax_amount = Decimal("0")
        tax_rate = Decimal("0")
    else:
        tax_rate = Decimal("19.00")
        tax_amount = subtotal * tax_rate / Decimal("100")
    total = subtotal + tax_amount

    today = date.today()
    invoice = Invoice(
        customer_id=data.customer_id,
        invoice_number=invoice_number,
        title=data.beschreibung,
        tax_exempt=is_exempt,
        positions=positions_json,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
        invoice_date=today,
        due_date=today + timedelta(days=14),
        notes=data.notes,
        status=InvoiceStatus.entwurf,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = customer.name
    return resp


@router.post("/{invoice_id}/payment", response_model=InvoiceResponse)
async def record_payment(
    invoice_id: uuid.UUID,
    data: PaymentRequest,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Teilzahlung erfassen."""
    from decimal import Decimal

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    if invoice.is_credit_note:
        raise HTTPException(status_code=400, detail="Für Gutschriften können keine Zahlungen erfasst werden")

    if data.amount <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Betrag muss positiv sein")

    invoice.amount_paid = (invoice.amount_paid or Decimal("0")) + data.amount

    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.bezahlt

    await db.flush()
    await db.refresh(invoice)

    activity = Activity(
        customer_id=invoice.customer_id,
        type="payment",
        title=f"Zahlung erfasst: {invoice.invoice_number}",
        description=f"{float(data.amount):.2f} € — Gesamt bezahlt: {float(invoice.amount_paid):.2f} € von {float(invoice.total):.2f} €",
    )
    db.add(activity)

    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = invoice.customer.name if invoice.customer else ""
    return resp


@router.post("/{invoice_id}/credit-note", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_note(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Gutschrift für eine Rechnung erstellen."""
    from datetime import date as date_type, timedelta
    from decimal import Decimal

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    if invoice.is_credit_note:
        raise HTTPException(status_code=400, detail="Für Gutschriften können keine weiteren Gutschriften erstellt werden")

    if invoice.status not in (InvoiceStatus.gestellt, InvoiceStatus.bezahlt, InvoiceStatus.ueberfaellig):
        raise HTTPException(
            status_code=400,
            detail="Gutschriften können nur für gestellte, bezahlte oder überfällige Rechnungen erstellt werden",
        )

    # Generate credit note number GS-YYYY-NNNN
    from datetime import datetime
    year = datetime.now().year
    gs_prefix = f"GS-{year}-"
    gs_result = await db.execute(
        select(Invoice.invoice_number)
        .where(Invoice.invoice_number.like(f"{gs_prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .limit(1)
    )
    last_gs = gs_result.scalar_one_or_none()
    if last_gs:
        next_seq = int(last_gs.split("-")[-1]) + 1
    else:
        next_seq = 1
    gs_number = f"{gs_prefix}{next_seq:04d}"

    # Negate all amounts
    neg_positions = []
    for pos in invoice.positions:
        neg_pos = dict(pos)
        neg_pos["gesamt"] = str(-abs(float(pos.get("gesamt", 0))))
        neg_pos["einzelpreis"] = str(-abs(float(pos.get("einzelpreis", 0))))
        neg_positions.append(neg_pos)

    today = date_type.today()
    credit_note = Invoice(
        customer_id=invoice.customer_id,
        invoice_number=gs_number,
        title=f"Gutschrift zu {invoice.invoice_number}",
        positions=neg_positions,
        subtotal=-abs(invoice.subtotal),
        tax_rate=invoice.tax_rate,
        tax_amount=-abs(invoice.tax_amount),
        total=-abs(invoice.total),
        invoice_date=today,
        due_date=today,
        status=InvoiceStatus.bezahlt,
        is_credit_note=True,
        credit_note_for=invoice.id,
        notes=f"Gutschrift zu Rechnung {invoice.invoice_number}",
    )
    db.add(credit_note)
    await db.flush()
    await db.refresh(credit_note)

    activity = Activity(
        customer_id=invoice.customer_id,
        type="invoice",
        title=f"Gutschrift {gs_number} erstellt",
        description=f"Gutschrift zu {invoice.invoice_number} — {float(credit_note.total):.2f} €",
    )
    db.add(activity)

    # Load customer for response
    result2 = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == credit_note.id)
    )
    credit_note = result2.scalar_one()

    resp = InvoiceResponse.model_validate(credit_note)
    resp.customer_name = credit_note.customer.name if credit_note.customer else ""
    return resp


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if invoice.status != InvoiceStatus.entwurf:
        raise HTTPException(
            status_code=400,
            detail="Nur Rechnungen im Status 'Entwurf' können gelöscht werden",
        )
    await db.delete(invoice)
