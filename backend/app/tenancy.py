"""Multi-tenant data isolation.

Every owned entity carries `owner_id` (via OwnedMixin). A request-scoped
ContextVar holds the current user's id; SQLAlchemy session events then:
  - auto-filter every ORM SELECT to the current owner (with_loader_criteria), and
  - auto-stamp owner_id on every newly inserted owned object (before_flush).

When the ContextVar is unset (login, bootstrap, the system cron) nothing is
scoped — those run with full/global access by design.
"""
import contextvars
import uuid

from sqlalchemy import ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria

# Current request's owner (user) id, or None for unscoped/system contexts.
current_owner_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_owner_id", default=None
)


class OwnedMixin:
    """Adds an owner_id FK. Nullable so the column can be added + backfilled on a
    live DB before the scoping code goes live; new rows are stamped automatically."""

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )


_owned_models: list[type] = []


def set_owned_models(models: list[type]) -> None:
    _owned_models.clear()
    _owned_models.extend(models)


def install_tenancy_events() -> None:
    @event.listens_for(Session, "do_orm_execute")
    def _scope_selects(state):  # noqa: ANN001
        # Canonical SQLAlchemy multi-tenant recipe: only plain SELECTs, skip
        # relationship/column lazy-loads (already constrained by their parent).
        if (not state.is_select) or state.is_column_load or state.is_relationship_load:
            return
        oid = current_owner_id.get()
        if oid is None:
            return
        for model in _owned_models:
            state.statement = state.statement.options(
                with_loader_criteria(model, model.owner_id == oid, include_aliases=True)
            )

    @event.listens_for(Session, "before_flush")
    def _stamp_owner(session, flush_context, instances):  # noqa: ANN001
        oid = current_owner_id.get()
        if oid is None:
            return
        for obj in session.new:
            if isinstance(obj, OwnedMixin) and getattr(obj, "owner_id", None) is None:
                obj.owner_id = oid
