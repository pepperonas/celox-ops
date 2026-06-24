from datetime import date as DateType

from pydantic import BaseModel


class ComplianceItem(BaseModel):
    """Status eines Pflichtdokuments für einen Kunden."""

    template_id: str
    name: str
    category: str
    signed: bool
    signed_at: DateType | None = None
    method: str | None = None
    attachment_id: str | None = None
    note: str | None = None


class ComplianceCustomer(BaseModel):
    customer_id: str
    name: str
    company: str | None = None
    total_required: int
    signed_count: int
    missing_count: int
    complete: bool
    items: list[ComplianceItem]


class RequiredTemplate(BaseModel):
    id: str
    name: str
    category: str


class ComplianceSummary(BaseModel):
    total_customers: int
    fully_compliant: int
    with_gaps: int
    total_missing: int


class ComplianceOverview(BaseModel):
    required_templates: list[RequiredTemplate]
    customers: list[ComplianceCustomer]
    summary: ComplianceSummary


class MarkRequest(BaseModel):
    customer_id: str
    template_id: str
    signed: bool = True
    signed_at: DateType | None = None
    note: str | None = None


class RequiredToggle(BaseModel):
    required: bool
