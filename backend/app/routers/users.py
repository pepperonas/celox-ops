import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, hash_password, require_admin, verify_password
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import PasswordChange, PasswordSet, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_response(u: User, works_for_username: str | None = None) -> UserResponse:
    return UserResponse(
        id=u.id, username=u.username, email=u.email, google_email=u.google_email,
        role=u.role.value, is_active=u.is_active, created_at=u.created_at,
        works_for_id=u.works_for_id, works_for_username=works_for_username,
    )


async def _validate_works_for(
    role: UserRole, works_for_id, db: AsyncSession, self_id=None
):
    """Mitarbeitende brauchen einen Arbeitsbereich; andere Rollen dürfen keinen
    haben. Der Chef muss existieren, aktiv und selbst kein Mitarbeiter sein
    (keine Ketten) und darf nicht der Nutzer selbst sein."""
    if role != UserRole.mitarbeiter:
        return None
    if not works_for_id:
        raise HTTPException(
            status_code=422,
            detail="Für die Rolle „Mitarbeiter“ muss ein Arbeitsbereich (works_for_id) gewählt werden.",
        )
    if self_id and works_for_id == self_id:
        raise HTTPException(status_code=422, detail="Ein Nutzer kann nicht für sich selbst arbeiten.")
    boss = (await db.execute(select(User).where(User.id == works_for_id))).scalar_one_or_none()
    if not boss or not boss.is_active:
        raise HTTPException(status_code=422, detail="Arbeitsbereich-Inhaber nicht gefunden oder inaktiv.")
    if boss.works_for_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Der gewählte Nutzer ist selbst Mitarbeiter — verschachtelte Arbeitsbereiche sind nicht möglich.",
        )
    return boss


async def _active_admin_count(db: AsyncSession, exclude_id: uuid.UUID | None = None) -> int:
    q = select(func.count()).select_from(User).where(
        User.role == UserRole.admin, User.is_active.is_(True)
    )
    if exclude_id is not None:
        q = q.where(User.id != exclude_id)
    return (await db.execute(q)).scalar_one()


# ---- Self-service (any authenticated user) ----

@router.get("/me/ical-token")
async def my_ical_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns (and lazily creates) the current user's personal iCal feed token."""
    if not current_user.ical_token:
        current_user.ical_token = secrets.token_urlsafe(24)
        await db.flush()
    return {"token": current_user.ical_token}


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Aktuelles Passwort falsch")
    current_user.password_hash = hash_password(data.new_password)
    await db.flush()


# ---- Admin user management ----

@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    names = {u.id: u.username for u in rows}
    return [_to_response(u, names.get(u.works_for_id) if u.works_for_id else None) for u in rows]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=422, detail="Ungültige Rolle")
    exists = (await db.execute(select(User).where(User.username == data.username))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Benutzername bereits vergeben")
    boss = await _validate_works_for(role, data.works_for_id, db)
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
        is_active=True,
        works_for_id=boss.id if boss else None,
        ical_token=secrets.token_urlsafe(24),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _to_response(user, boss.username if boss else None)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    if data.email is not None:
        user.email = data.email
    if data.google_email is not None:
        user.google_email = data.google_email.strip().lower() or None
    if data.role is not None:
        try:
            new_role = UserRole(data.role)
        except ValueError:
            raise HTTPException(status_code=422, detail="Ungültige Rolle")
        # Don't demote the last active admin.
        if user.role == UserRole.admin and new_role != UserRole.admin:
            if await _active_admin_count(db, exclude_id=user.id) == 0:
                raise HTTPException(status_code=400, detail="Letzter Admin kann nicht herabgestuft werden")
        # Arbeitsbereich passend zur (neuen) Rolle setzen bzw. entfernen.
        target_works_for = data.works_for_id if data.works_for_id is not None else user.works_for_id
        boss = await _validate_works_for(new_role, target_works_for, db, self_id=user.id)
        user.works_for_id = boss.id if boss else None
        user.role = new_role
    if data.is_active is not None:
        if not data.is_active:
            if user.id == current_user.id:
                raise HTTPException(status_code=400, detail="Eigenes Konto kann nicht deaktiviert werden")
            if user.role == UserRole.admin and await _active_admin_count(db, exclude_id=user.id) == 0:
                raise HTTPException(status_code=400, detail="Letzter Admin kann nicht deaktiviert werden")
        user.is_active = data.is_active
    await db.flush()
    await db.refresh(user)
    return _to_response(user)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(require_admin)])
async def set_user_password(
    user_id: uuid.UUID, data: PasswordSet, db: AsyncSession = Depends(get_db)
) -> None:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    user.password_hash = hash_password(data.password)
    await db.flush()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Eigenes Konto kann nicht gelöscht werden")
    if user.role == UserRole.admin and await _active_admin_count(db, exclude_id=user.id) == 0:
        raise HTTPException(status_code=400, detail="Letzter Admin kann nicht gelöscht werden")
    # NB: owner_id FKs are ON DELETE CASCADE → this removes the user's entire workspace.
    await db.delete(user)
    await db.flush()
