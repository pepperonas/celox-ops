import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.customer import Customer
from app.schemas.contract import (
    ContractCreate,
    ContractDetail,
    ContractResponse,
    ContractUpdate,
)

router = APIRouter(
    prefix="/api/contracts",
    tags=["contracts"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ContractResponse])
async def list_contracts(
    customer_id: uuid.UUID | None = Query(None),
    contract_status: ContractStatus | None = Query(None, alias="status"),
    contract_type: ContractType | None = Query(None, alias="type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
) -> list[ContractResponse]:
    query = select(Contract).options(joinedload(Contract.customer))

    if customer_id:
        query = query.where(Contract.customer_id == customer_id)
    if contract_status:
        query = query.where(Contract.status == contract_status)
    if contract_type:
        query = query.where(Contract.type == contract_type)

    sort_column = getattr(Contract, sort_by, Contract.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    contracts = result.scalars().unique().all()

    responses = []
    for contract in contracts:
        resp = ContractResponse.model_validate(contract)
        resp.customer_name = contract.customer.name if contract.customer else ""
        responses.append(resp)
    return responses


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContractDetail:
    result = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer), joinedload(Contract.invoices))
        .where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Vertrag nicht gefunden")

    detail = ContractDetail.model_validate(contract)
    detail.customer_name = contract.customer.name if contract.customer else ""
    detail.invoices_count = len(contract.invoices)
    return detail


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    cust = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    contract = Contract(**data.model_dump())
    db.add(contract)
    await db.flush()
    await db.refresh(contract)

    resp = ContractResponse.model_validate(contract)
    resp.customer_name = customer.name
    return resp


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: uuid.UUID,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    result = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer))
        .where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Vertrag nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)

    await db.flush()
    await db.refresh(contract)

    result = await db.execute(
        select(Contract)
        .options(joinedload(Contract.customer))
        .where(Contract.id == contract_id)
    )
    contract = result.scalar_one()

    resp = ContractResponse.model_validate(contract)
    resp.customer_name = contract.customer.name if contract.customer else ""
    return resp


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Vertrag nicht gefunden")
    await db.delete(contract)
