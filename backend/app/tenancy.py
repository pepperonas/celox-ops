"""Multi-tenant data isolation.

Every owned entity carries `owner_id` (via OwnedMixin). A request-scoped
ContextVar holds the current user's id; SQLAlchemy session events then:
  - auto-filter every ORM SELECT to the current owner (with_loader_criteria), and
  - auto-stamp owner_id on every newly inserted owned object (before_flush).

When the ContextVar is unset (login, bootstrap, the system cron) nothing is
scoped — those run with full/global access by design.
"""
import contextlib
import contextvars
import uuid

from sqlalchemy import ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria

# Current request's owner (user) id, or None for unscoped/system contexts.
current_owner_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_owner_id", default=None
)

# Weich gelöschte Datensätze mitliefern? Standard: nein.
#
# Der Papierkorb (`rainmaker_leads.deleted_at`) wird hier ausgefiltert und nicht
# in den Routern: Leads werden an rund zehn Stellen gelesen (Liste, Detail,
# Dedup-Index, Duplikatsuche, Heute-Queue, Statistik, Traumziel, globale Suche,
# Analyse-Warteschlange, To-do-Verknüpfung). Eine vergessene Stelle würde einen
# gelöschten Lead wieder auftauchen lassen — oder, beim Dedup-Index, einen Import
# gegen einen unsichtbaren Datensatz blocken. Dieselbe Begründung wie beim
# Mandantenfilter: zentral, damit es nicht vergessen werden kann.
#
# Genau zwei Stellen setzen das Flag bewusst auf True: die Papierkorb-Ansicht und
# das Wiederherstellen/endgültige Löschen.
include_soft_deleted: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "include_soft_deleted", default=False
)


class OwnedMixin:
    """Adds an owner_id FK. Nullable so the column can be added + backfilled on a
    live DB before the scoping code goes live; new rows are stamped automatically."""

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )


@contextlib.contextmanager
def soft_deleted_visible():
    """Innerhalb dieses Blocks liefern SELECTs auch weich gelöschte Zeilen.

    Nötig für den Papierkorb selbst (anzeigen, wiederherstellen, endgültig
    entfernen, Tageszähler). Ohne den Schalter wären die Zeilen unsichtbar — der
    Tageszähler hätte still immer 0 gemeldet und der Deckel nie gegriffen.

    Als Kontextmanager, damit der Wert auch bei einer Exception zurückgesetzt
    wird: ein hängengebliebenes True würde für den Rest des Requests gelöschte
    Leads in normale Listen einblenden.
    """
    token = include_soft_deleted.set(True)
    try:
        yield
    finally:
        include_soft_deleted.reset(token)


_owned_models: list[type] = []
_soft_delete_models: list[type] = []


def set_owned_models(models: list[type]) -> None:
    _owned_models.clear()
    _owned_models.extend(models)
    # Modelle mit Papierkorb erkennen wir am Attribut — so kann ein neues
    # weich-löschbares Modell nicht vergessen werden, solange es owned ist.
    _soft_delete_models.clear()
    _soft_delete_models.extend(m for m in models if hasattr(m, "deleted_at"))


def install_tenancy_events() -> None:
    @event.listens_for(Session, "do_orm_execute")
    def _scope_selects(state):  # noqa: ANN001
        # Canonical SQLAlchemy multi-tenant recipe: only plain SELECTs, skip
        # relationship/column lazy-loads (already constrained by their parent).
        if (not state.is_select) or state.is_column_load or state.is_relationship_load:
            return
        # Papierkorb ausfiltern — unabhängig davon, ob ein Mandant gesetzt ist:
        # der Cron und die Hintergrund-Worker laufen ohne ContextVar, sollen aber
        # genauso keine gelöschten Leads verarbeiten.
        if not include_soft_deleted.get():
            for model in _soft_delete_models:
                state.statement = state.statement.options(
                    with_loader_criteria(
                        model, model.deleted_at.is_(None), include_aliases=True
                    )
                )

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
