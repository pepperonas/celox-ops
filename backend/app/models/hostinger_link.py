"""Bestätigte Zuordnung Hostinger-Abo → Domain.

Die API verknüpft ein Domain-Abo nicht mit einer Domain (siehe
`services/hostinger.py`); die Zuordnung wird aus der Bestellreihenfolge
abgeleitet. Sobald der Mensch sie im Dialog bestätigt oder korrigiert, gehört
sie hierher — damit der Import im nächsten Jahr **nicht wieder ableiten muss**
und eine Korrektur nicht bei jedem Lauf erneut fällig wird.

Neue Tabelle ⇒ `Base.metadata.create_all` erzeugt sie beim Start, keine
Migration nötig (Repo-Konvention: nur neue *Spalten* brauchen ein `ALTER`).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base
from app.tenancy import OwnedMixin


class HostingerDomainLink(OwnedMixin, Base):
    __tablename__ = "hostinger_domain_links"
    # Ein Abo hat genau eine Domain — pro Arbeitsbereich, denn zwei Nutzer können
    # dasselbe Hostinger-Konto verwenden.
    __table_args__ = (
        Index("uq_hostinger_link_owner_sub", "owner_id", "subscription_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subscription_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
