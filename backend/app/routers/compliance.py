import os
import uuid
from datetime import date as DateType

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.attachment import Attachment
from app.models.compliance_record import ComplianceRecord
from app.models.customer import Customer
from app.models.document_template import DocumentTemplate
from app.routers.attachments import (
    ALLOWED_MIME_TYPES,
    ATTACHMENTS_DIR,
    MAX_FILE_SIZE,
    _ensure_dir,
    _safe_filename,
)
from app.schemas.compliance import (
    ComplianceCustomer,
    ComplianceItem,
    ComplianceOverview,
    ComplianceSummary,
    MarkRequest,
    RequiredTemplate,
    RequiredToggle,
)

router = APIRouter(
    prefix="/api/compliance",
    tags=["compliance"],
    dependencies=[Depends(get_current_user)],
)


async def _required_templates(db: AsyncSession) -> list[DocumentTemplate]:
    result = await db.execute(
        select(DocumentTemplate)
        .where(DocumentTemplate.compliance_required.is_(True))
        .order_by(DocumentTemplate.category, DocumentTemplate.name)
    )
    return list(result.scalars().all())


def _build_items(
    templates: list[DocumentTemplate],
    records: dict[uuid.UUID, ComplianceRecord],
) -> list[ComplianceItem]:
    items: list[ComplianceItem] = []
    for t in templates:
        rec = records.get(t.id)
        signed = bool(rec and rec.signed_at)
        items.append(
            ComplianceItem(
                template_id=str(t.id),
                name=t.name,
                category=t.category,
                signed=signed,
                signed_at=rec.signed_at if rec else None,
                method=rec.method if rec else None,
                attachment_id=str(rec.attachment_id) if rec and rec.attachment_id else None,
                note=rec.note if rec else None,
            )
        )
    return items


@router.get("/overview", response_model=ComplianceOverview)
async def overview(db: AsyncSession = Depends(get_db)) -> ComplianceOverview:
    templates = await _required_templates(db)
    template_ids = [t.id for t in templates]

    customers = (await db.execute(select(Customer).order_by(Customer.name))).scalars().all()

    # All relevant records in one query, indexed by (customer_id, template_id)
    records_by_customer: dict[uuid.UUID, dict[uuid.UUID, ComplianceRecord]] = {}
    if template_ids:
        recs = (
            await db.execute(
                select(ComplianceRecord).where(ComplianceRecord.template_id.in_(template_ids))
            )
        ).scalars().all()
        for r in recs:
            records_by_customer.setdefault(r.customer_id, {})[r.template_id] = r

    total_required = len(templates)
    out_customers: list[ComplianceCustomer] = []
    fully = 0
    total_missing = 0
    for c in customers:
        items = _build_items(templates, records_by_customer.get(c.id, {}))
        signed_count = sum(1 for i in items if i.signed)
        missing = total_required - signed_count
        complete = total_required > 0 and missing == 0
        if complete:
            fully += 1
        total_missing += missing
        out_customers.append(
            ComplianceCustomer(
                customer_id=str(c.id),
                name=c.name,
                company=c.company,
                total_required=total_required,
                signed_count=signed_count,
                missing_count=missing,
                complete=complete,
                items=items,
            )
        )

    # Kunden mit Lücken zuerst
    out_customers.sort(key=lambda x: (x.complete, x.name.lower()))

    return ComplianceOverview(
        required_templates=[
            RequiredTemplate(id=str(t.id), name=t.name, category=t.category) for t in templates
        ],
        customers=out_customers,
        summary=ComplianceSummary(
            total_customers=len(customers),
            fully_compliant=fully,
            with_gaps=len(customers) - fully,
            total_missing=total_missing,
        ),
    )


@router.get("/customer/{customer_id}", response_model=ComplianceCustomer)
async def customer_status(
    customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ComplianceCustomer:
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    templates = await _required_templates(db)
    template_ids = [t.id for t in templates]
    records: dict[uuid.UUID, ComplianceRecord] = {}
    if template_ids:
        recs = (
            await db.execute(
                select(ComplianceRecord).where(
                    ComplianceRecord.customer_id == customer_id,
                    ComplianceRecord.template_id.in_(template_ids),
                )
            )
        ).scalars().all()
        records = {r.template_id: r for r in recs}

    items = _build_items(templates, records)
    signed_count = sum(1 for i in items if i.signed)
    total_required = len(templates)
    missing = total_required - signed_count
    return ComplianceCustomer(
        customer_id=str(customer.id),
        name=customer.name,
        company=customer.company,
        total_required=total_required,
        signed_count=signed_count,
        missing_count=missing,
        complete=total_required > 0 and missing == 0,
        items=items,
    )


async def _get_or_create_record(
    db: AsyncSession, customer_id: uuid.UUID, template_id: uuid.UUID
) -> ComplianceRecord:
    rec = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.customer_id == customer_id,
                ComplianceRecord.template_id == template_id,
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        rec = ComplianceRecord(customer_id=customer_id, template_id=template_id)
        db.add(rec)
    return rec


@router.post("/mark", response_model=ComplianceItem)
async def mark(data: MarkRequest, db: AsyncSession = Depends(get_db)) -> ComplianceItem:
    """Manuell als unterschrieben markieren (signed=True) oder Markierung entfernen (signed=False)."""
    try:
        cid = uuid.UUID(data.customer_id)
        tid = uuid.UUID(data.template_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Ungültige ID")

    template = await db.get(DocumentTemplate, tid)
    if not template or not await db.get(Customer, cid):
        raise HTTPException(status_code=404, detail="Kunde oder Vorlage nicht gefunden")

    rec = await _get_or_create_record(db, cid, tid)
    if data.signed:
        rec.signed_at = data.signed_at or DateType.today()
        rec.method = "manual"
        rec.note = data.note
    else:
        # Markierung entfernen → Datensatz löschen (die Datei im Anhang bleibt erhalten)
        await db.delete(rec)
        await db.flush()
        return ComplianceItem(
            template_id=str(tid), name=template.name, category=template.category, signed=False
        )
    await db.flush()
    return ComplianceItem(
        template_id=str(tid),
        name=template.name,
        category=template.category,
        signed=True,
        signed_at=rec.signed_at,
        method=rec.method,
        attachment_id=str(rec.attachment_id) if rec.attachment_id else None,
        note=rec.note,
    )


@router.post("/upload", response_model=ComplianceItem)
async def upload_signed(
    file: UploadFile = File(...),
    customer_id: str = Form(...),
    template_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> ComplianceItem:
    """Unterschriebenes PDF hochladen → als Anhang speichern + Pflichtdokument als erfüllt markieren."""
    try:
        cid = uuid.UUID(customer_id)
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Ungültige ID")

    template = await db.get(DocumentTemplate, tid)
    if not template or not await db.get(Customer, cid):
        raise HTTPException(status_code=404, detail="Kunde oder Vorlage nicht gefunden")

    content_type = (file.content_type or "application/octet-stream").lower().split(";")[0].strip()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Dateityp '{content_type}' nicht erlaubt.",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Datei zu groß (max. 20 MB)."
        )

    _ensure_dir()
    file_id = uuid.uuid4()
    original_name = _safe_filename(file.filename or f"{template.name}.pdf")
    stored_name = f"{file_id}_{original_name}"
    file_path = os.path.join(ATTACHMENTS_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        attachment = Attachment(
            id=file_id,
            customer_id=cid,
            filename=stored_name,
            original_name=original_name,
            content_type=content_type,
            size=len(content),
            description=f"Unterschrieben: {template.name}",
        )
        db.add(attachment)
        await db.flush()

        rec = await _get_or_create_record(db, cid, tid)
        rec.signed_at = DateType.today()
        rec.method = "upload"
        rec.attachment_id = file_id
        await db.flush()
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return ComplianceItem(
        template_id=str(tid),
        name=template.name,
        category=template.category,
        signed=True,
        signed_at=rec.signed_at,
        method=rec.method,
        attachment_id=str(file_id),
        note=rec.note,
    )


@router.put("/templates/{template_id}/required", response_model=RequiredTemplate)
async def set_required(
    template_id: uuid.UUID, data: RequiredToggle, db: AsyncSession = Depends(get_db)
) -> RequiredTemplate:
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    template.compliance_required = data.required
    await db.flush()
    return RequiredTemplate(id=str(template.id), name=template.name, category=template.category)
