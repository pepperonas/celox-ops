import os
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.attachment import Attachment

ATTACHMENTS_DIR = "/data/attachments"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

router = APIRouter(
    prefix="/api/attachments",
    tags=["attachments"],
    dependencies=[Depends(get_current_user)],
)


def _ensure_dir():
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Strip directory components to prevent path traversal."""
    return PurePosixPath(name).name or "unnamed"


def _attachment_to_dict(a: Attachment) -> dict:
    return {
        "id": str(a.id),
        "customer_id": str(a.customer_id) if a.customer_id else None,
        "order_id": str(a.order_id) if a.order_id else None,
        "contract_id": str(a.contract_id) if a.contract_id else None,
        "filename": a.filename,
        "original_name": a.original_name,
        "content_type": a.content_type,
        "size": a.size,
        "description": a.description,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("")
async def upload_attachment(
    file: UploadFile = File(...),
    customer_id: str | None = Form(None),
    order_id: str | None = Form(None),
    contract_id: str | None = Form(None),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ensure_dir()

    file_id = uuid.uuid4()
    original_name = _safe_filename(file.filename or "unnamed")
    stored_name = f"{file_id}_{original_name}"
    file_path = os.path.join(ATTACHMENTS_DIR, stored_name)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Datei zu groß (max. 20 MB).",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = Attachment(
        id=file_id,
        customer_id=uuid.UUID(customer_id) if customer_id else None,
        order_id=uuid.UUID(order_id) if order_id else None,
        contract_id=uuid.UUID(contract_id) if contract_id else None,
        filename=stored_name,
        original_name=original_name,
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        description=description,
    )
    try:
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return _attachment_to_dict(attachment)


@router.get("")
async def list_attachments(
    customer_id: str | None = Query(None),
    order_id: str | None = Query(None),
    contract_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(Attachment)

    if customer_id:
        query = query.where(Attachment.customer_id == uuid.UUID(customer_id))
    if order_id:
        query = query.where(Attachment.order_id == uuid.UUID(order_id))
    if contract_id:
        query = query.where(Attachment.contract_id == uuid.UUID(contract_id))

    query = query.order_by(Attachment.created_at.desc())
    result = await db.execute(query)
    attachments = result.scalars().all()

    return [_attachment_to_dict(a) for a in attachments]


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Attachment).where(Attachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Anhang nicht gefunden")

    file_path = os.path.join(ATTACHMENTS_DIR, attachment.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")

    return FileResponse(
        path=file_path,
        filename=attachment.original_name,
        media_type=attachment.content_type,
    )


class AttachmentUpdate(BaseModel):
    description: str | None = None
    notes: str | None = None


@router.patch("/{attachment_id}")
async def update_attachment(
    attachment_id: uuid.UUID,
    data: AttachmentUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Attachment).where(Attachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Anhang nicht gefunden")

    if data.description is not None:
        attachment.description = data.description
    if data.notes is not None:
        attachment.notes = data.notes
    await db.flush()
    await db.refresh(attachment)
    return _attachment_to_dict(attachment)


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Attachment).where(Attachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Anhang nicht gefunden")

    file_path = os.path.join(ATTACHMENTS_DIR, attachment.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    await db.delete(attachment)
