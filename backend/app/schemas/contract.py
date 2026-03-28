import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.contract import BillingCycle, ContractStatus, ContractType


class ContractBase(BaseModel):
    customer_id: uuid.UUID
    title: str
    type: ContractType
    description: str | None = None
    monthly_amount: Decimal
    billing_cycle: BillingCycle = BillingCycle.monatlich
    start_date: date
    end_date: date | None = None
    auto_renew: bool = True
    notice_period_days: int = 30
    status: ContractStatus = ContractStatus.aktiv


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    title: str | None = None
    type: ContractType | None = None
    description: str | None = None
    monthly_amount: Decimal | None = None
    billing_cycle: BillingCycle | None = None
    start_date: date | None = None
    end_date: date | None = None
    auto_renew: bool | None = None
    notice_period_days: int | None = None
    status: ContractStatus | None = None


class ContractResponse(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    last_invoiced_date: date | None = None
    customer_name: str = ""
    created_at: datetime
    updated_at: datetime


class ContractDetail(ContractResponse):
    invoices_count: int = 0
