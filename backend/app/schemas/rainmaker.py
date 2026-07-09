import uuid
from datetime import date as DateType, datetime, time as TimeType
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.rainmaker_activity import (
    RainmakerActivityStatus,
    RainmakerActivityType,
    RainmakerOutcome,
)
from app.models.rainmaker_lead import RainmakerLeadStatus, RainmakerPriority
from app.models.rainmaker_settings import RainmakerDreamMode, RainmakerReminderChannel
from app.models.rainmaker_template import RainmakerTemplateChannel


# --------------------------------------------------------------------------- #
#  Leads
# --------------------------------------------------------------------------- #
class RainmakerLeadBase(BaseModel):
    company: str
    contact_name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    source: str | None = None
    status: RainmakerLeadStatus = RainmakerLeadStatus.new
    priority: RainmakerPriority = RainmakerPriority.medium
    value_estimate: Decimal | None = None
    tags: list[str] | None = None
    notes: str | None = None


class RainmakerLeadCreate(RainmakerLeadBase):
    pass


class LinkedInImportRow(BaseModel):
    """Eine geparste Zeile aus LinkedIns Connections.csv (kanonische Keys)."""
    first_name: str = ""
    last_name: str = ""
    url: str = ""
    email: str = ""
    company: str = ""
    position: str = ""
    connected_on: str = ""


class LinkedInPreviewRow(LinkedInImportRow):
    duplicate: bool = False


class LinkedInImportRequest(BaseModel):
    rows: list[LinkedInImportRow]


class LinkedInImportResult(BaseModel):
    created: int
    skipped_duplicates: int


class RainmakerLeadUpdate(BaseModel):
    company: str | None = None
    contact_name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    source: str | None = None
    status: RainmakerLeadStatus | None = None
    priority: RainmakerPriority | None = None
    value_estimate: Decimal | None = None
    tags: list[str] | None = None
    notes: str | None = None


class RainmakerLeadResponse(RainmakerLeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Computed "next action" summary (populated by the activation engine).
    next_action_type: RainmakerActivityType | None = None
    next_action_due: DateType | None = None
    next_action_id: uuid.UUID | None = None
    # True when the lead is active but has no planned activity ("rotting").
    needs_next_action: bool = False


# --------------------------------------------------------------------------- #
#  Activities
# --------------------------------------------------------------------------- #
class RainmakerActivityCreate(BaseModel):
    type: RainmakerActivityType
    due_date: DateType | None = None
    notes: str | None = None
    goal_id: uuid.UUID | None = None


class RainmakerActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    goal_id: uuid.UUID | None = None
    type: RainmakerActivityType
    status: RainmakerActivityStatus
    due_date: DateType | None = None
    completed_at: datetime | None = None
    outcome: RainmakerOutcome | None = None
    notes: str | None = None
    created_at: datetime


class RainmakerActivityComplete(BaseModel):
    """Logs an activity as done. Enforces a next action UNLESS the lead is being
    closed (won/lost/dormant). Validated server-side in the endpoint."""

    outcome: RainmakerOutcome | None = None
    notes: str | None = None
    # Next planned action (required unless close_status is set):
    next_type: RainmakerActivityType | None = None
    next_due: DateType | None = None
    next_goal_id: uuid.UUID | None = None
    # Closing the lead instead of planning a next action:
    close_status: RainmakerLeadStatus | None = None


# --------------------------------------------------------------------------- #
#  "Heute" / Activation engine
# --------------------------------------------------------------------------- #
class RainmakerLeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    status: RainmakerLeadStatus
    priority: RainmakerPriority
    value_estimate: Decimal | None = None


class RainmakerTodayItem(BaseModel):
    activity: RainmakerActivityResponse
    lead: RainmakerLeadSummary
    days_overdue: int = 0


class RainmakerProgress(BaseModel):
    daily_quota: int
    done_today: int
    current_streak: int
    longest_streak: int
    total_points: int
    freeze_remaining: int = 0


class RainmakerGoalProgress(BaseModel):
    id: uuid.UUID
    name: str
    suggested_type: RainmakerActivityType
    daily_target: int
    done_today: int


class RainmakerTodayResponse(BaseModel):
    date: DateType
    queue: list[RainmakerTodayItem]
    rotting: list[RainmakerLeadSummary]
    progress: RainmakerProgress
    goals: list[RainmakerGoalProgress]
    total_leads: int


# --------------------------------------------------------------------------- #
#  Statistik
# --------------------------------------------------------------------------- #
class RmTypeCount(BaseModel):
    type: RainmakerActivityType
    count: int


class RmDayCount(BaseModel):
    date: DateType
    count: int


class RmStatusCount(BaseModel):
    status: RainmakerLeadStatus
    count: int


class RainmakerStatsResponse(BaseModel):
    activity_by_type: list[RmTypeCount]
    activity_by_day: list[RmDayCount]
    funnel: list[RmStatusCount]
    total_leads: int
    won_count: int
    lost_count: int
    open_value: Decimal | None = None
    won_value: Decimal | None = None
    current_streak: int
    longest_streak: int
    total_points: int


# --------------------------------------------------------------------------- #
#  Settings
# --------------------------------------------------------------------------- #
class RainmakerSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    daily_quota: int
    reminder_enabled: bool
    reminder_time: TimeType
    reminder_channel: RainmakerReminderChannel
    telegram_chat_id: str | None = None
    freezes_per_month: int
    # Traumziel (dream goal)
    dream_goal_key: str | None = None
    dream_goal_name: str | None = None
    dream_goal_price: Decimal
    dream_savings_rate_pct: int
    dream_avg_deal_value: Decimal
    dream_contacts_per_win: int
    dream_start_date: DateType | None = None
    dream_mode: RainmakerDreamMode


class RainmakerSettingsUpdate(BaseModel):
    daily_quota: int | None = None
    reminder_enabled: bool | None = None
    reminder_time: TimeType | None = None
    reminder_channel: RainmakerReminderChannel | None = None
    telegram_chat_id: str | None = None
    freezes_per_month: int | None = None
    # Traumziel (dream goal)
    dream_goal_key: str | None = None
    dream_goal_name: str | None = None
    dream_goal_price: Decimal | None = None
    dream_savings_rate_pct: int | None = None
    dream_avg_deal_value: Decimal | None = None
    dream_contacts_per_win: int | None = None
    dream_start_date: DateType | None = None
    dream_mode: RainmakerDreamMode | None = None


# --------------------------------------------------------------------------- #
#  Templates
# --------------------------------------------------------------------------- #
class RainmakerTemplateBase(BaseModel):
    channel: RainmakerTemplateChannel
    name: str
    subject: str | None = None
    body: str


class RainmakerTemplateCreate(RainmakerTemplateBase):
    pass


class RainmakerTemplateUpdate(BaseModel):
    channel: RainmakerTemplateChannel | None = None
    name: str | None = None
    subject: str | None = None
    body: str | None = None


class RainmakerTemplateResponse(RainmakerTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
#  Goals (Akquise-Ziele)
# --------------------------------------------------------------------------- #
class RainmakerGoalBase(BaseModel):
    name: str
    suggested_type: RainmakerActivityType
    daily_target: int = 3
    active: bool = True
    sort_order: int = 0


class RainmakerGoalCreate(RainmakerGoalBase):
    pass


class RainmakerGoalUpdate(BaseModel):
    name: str | None = None
    suggested_type: RainmakerActivityType | None = None
    daily_target: int | None = None
    active: bool | None = None
    sort_order: int | None = None


class RainmakerGoalResponse(RainmakerGoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
#  Traumziel (dream goal) — expected-value motivation engine
# --------------------------------------------------------------------------- #
class RainmakerDreamResponse(BaseModel):
    # Goal + assumptions (mirrors the settings so the view is self-contained).
    goal_key: str | None = None
    goal_name: str
    goal_price: Decimal
    savings_rate_pct: int
    avg_deal_value: Decimal
    contacts_per_win: int
    start_date: DateType
    mode: RainmakerDreamMode

    # Engine constants for client-side scenario math.
    ev_per_contact: Decimal
    ev_weights: dict[str, float]

    # Progress since start_date.
    counts_by_type: list[RmTypeCount]
    activities_ev: Decimal        # statistical value of all completed actions
    won_count: int
    won_value: Decimal            # sum of won leads' value_estimate
    won_ev: Decimal               # won_value × savings rate ("realized")
    invoices_paid: Decimal        # paid invoice totals since start
    invoices_ev: Decimal          # invoices_paid × savings rate
    saved_total: Decimal          # mode-dependent primary progress value
    pct: float                    # saved_total / goal_price, capped at 1.0

    # Momentum.
    today_ev: Decimal             # value earned today
    pace_per_day: Decimal         # Ø €/day over the last 28 days (mode-aware)
    projected_date: DateType | None = None
    days_active: int
