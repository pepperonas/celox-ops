import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.customer import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    # Arbeitet IM Arbeitsbereich eines anderen Nutzers (works_for_id) und darf
    # dort alles anlegen/bearbeiten, aber nichts löschen oder zusammenführen.
    # Die Sperre sitzt serverseitig in middleware/permissions.py.
    mitarbeiter = "mitarbeiter"
    # Vertrieb: arbeitet IM Arbeitsbereich eines anderen und sieht dort NUR die
    # Pipeline (Leads) plus die Akquise-Vorlagen lesend. Darf Leads anlegen,
    # ändern und löschen — Löschen wirkt aber als Papierkorb (umkehrbar) und ist
    # pro Tag gedeckelt. Kein E-Mail-Versand, keine kostenpflichtigen
    # KI-Funktionen. Der Zuschnitt steht als Erlaubnisliste in
    # `middleware/role_scope.py` (deny-by-default).
    verkaeufer = "verkaeufer"


# Rollen ohne destruktive Rechte (kein DELETE, kein Merge).
# `verkaeufer` steht hier bewusst NICHT: Löschen ist ausdrücklich erlaubt, aber
# umkehrbar (Papierkorb) und gedeckelt. Ein Verbot wäre die falsche Antwort —
# Leads aussortieren ist Kernarbeit im Vertrieb.
NON_DESTRUCTIVE_ROLES = {UserRole.mitarbeiter}

# Rollen, die auf eine Erlaubnisliste beschränkt sind (deny-by-default).
SCOPED_ROLES = {UserRole.verkaeufer}

# Rollen, die zwingend in einem fremden Arbeitsbereich arbeiten (works_for_id
# ist Pflicht) — sonst hätten sie einen leeren eigenen Bereich und die Rolle
# wäre sinnlos.
ROLES_REQUIRING_WORKSPACE = {UserRole.mitarbeiter, UserRole.verkaeufer}

# Wie viele Leads darf ein Verkäufer pro Geschäftstag in den Papierkorb legen?
# Begrenzt eine Serie von Irrtümern (oder ein Skript), ohne normale Arbeit zu
# behindern: 10 Aussortierungen am Tag sind viel, 200 sind ein Unfall.
VERKAEUFER_DAILY_DELETE_CAP = 10

# Wie lange bleibt ein weich gelöschter Lead wiederherstellbar?
TRASH_RETENTION_DAYS = 30


class User(Base):
    """Application user. celox ops is multi-tenant: each user owns an isolated
    workspace (data scoped via owner_id on entities). Accounts are created by an
    admin — there is no public self-registration.

    Ausnahme: Nutzer mit `works_for_id` teilen den Arbeitsbereich ihres Chefs
    (siehe `workspace_owner_id`) — für Mitarbeitende, die auf denselben Leads
    arbeiten sollen."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        default=UserRole.user,
        server_default="user",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    # Geteilter Arbeitsbereich: ist das gesetzt, arbeitet dieser Nutzer auf den
    # Daten des verlinkten Nutzers (Tenancy löst darüber den owner_id auf).
    # NULL = eigener Arbeitsbereich (Standard, alle Bestandsnutzer).
    works_for_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Verknüpftes Google-Konto für "Sign in with Google" (nullable = kein
    # Google-Login für diesen Nutzer). Vergleich case-insensitiv.
    google_email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    # Per-user TOTP secret (nullable = 2FA off for this user).
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Per-user secret token for the personal iCal feed (scoped to this user's data).
    ical_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def may_manage_api_keys(user) -> bool:
    """Darf dieser Nutzer die API-Schlüssel des Arbeitsbereichs ändern?

    Nein für Mitarbeitende und Verkäufer: sie arbeiten IM Bereich ihres Inhabers
    und nutzen dessen Schlüssel (und dessen Abrechnung). Ihn austauschen oder
    entfernen wäre eine Entscheidung über fremdes Geld.
    """
    return getattr(user, "role", None) not in {UserRole.mitarbeiter, UserRole.verkaeufer}


def may_administer_leads(user) -> bool:
    """Darf dieser Nutzer den Papierkorb und das Änderungsprotokoll verwalten —
    also Löschungen zurückholen, endgültig entfernen und Änderungen zurücknehmen?

    Nur der Bereichs-Inhaber (bzw. ein Admin). Die Aufsicht über die Arbeit eines
    Verkäufers darf nicht bei ihm selbst liegen; sonst wäre der Papierkorb kein
    Sicherheitsnetz, sondern ein Zwischenschritt beim Löschen.
    """
    return getattr(user, "role", None) in {UserRole.admin, UserRole.user}


def workspace_owner_id(user: "User") -> uuid.UUID:
    """Wessen Daten sieht dieser Nutzer? Mitarbeitende arbeiten im Bereich ihres
    Chefs, alle anderen in ihrem eigenen. Einzige Stelle, die das entscheidet."""
    return user.works_for_id or user.id
