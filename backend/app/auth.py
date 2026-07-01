import base64
import io
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.tenancy import current_owner_id

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Rate limiter — 5 login attempts per minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=[])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    username: str
    role: str
    totp_enabled: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungültig oder abgelaufen",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    payload = verify_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungültig",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Konto nicht gefunden oder deaktiviert",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Activate multi-tenant scoping for the rest of this request.
    current_owner_id.set(user.id)
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Adminrechte erforderlich")
    return current_user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = (
        await db.execute(select(User).where(User.username == form_data.username))
    ).scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto deaktiviert",
        )

    # 2FA — if this user has a TOTP secret, require code in the scope field.
    if user.totp_secret:
        totp_code = (form_data.scopes[0] if form_data.scopes else "").strip()
        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA-Code erforderlich",
            )
        if not pyotp.TOTP(user.totp_secret).verify(totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA-Code ungültig",
            )

    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserInfo)
async def me(current_user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(
        username=current_user.username,
        role=current_user.role.value,
        totp_enabled=bool(current_user.totp_secret),
    )


@router.get("/info")
async def auth_info() -> dict:
    """Public endpoint for the login page. 2FA is per-user now, so the login flow
    surfaces the 2FA prompt via a 401 on the first attempt."""
    return {"totp_enabled": False}


@router.get("/2fa/setup")
async def setup_2fa(current_user: User = Depends(get_current_user)) -> Response:
    """Generates a new TOTP secret + QR code as PNG (persisted via account settings)."""
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.username,
        issuer_name=f"celox ops ({settings.BUSINESS_NAME or 'celox.io'})",
    )
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={
            "X-TOTP-Secret": secret,
            "X-TOTP-Hint": "Persist via account settings to activate 2FA",
        },
    )


class TwoFAEnable(BaseModel):
    secret: str
    code: str


class TwoFADisable(BaseModel):
    code: str


@router.get("/2fa/init")
async def init_2fa(current_user: User = Depends(get_current_user)) -> dict:
    """Generate a fresh candidate TOTP secret + QR (data URL). NOT persisted yet —
    the client must confirm a valid code via /2fa/enable to activate."""
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.username,
        issuer_name=f"celox ops ({settings.BUSINESS_NAME or 'celox.io'})",
    )
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"secret": secret, "otpauth_uri": uri, "qr": qr_data_url}


@router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_2fa(
    data: TwoFAEnable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Activate 2FA after verifying a code against the candidate secret."""
    if not pyotp.TOTP(data.secret).verify(data.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Code ungültig")
    current_user.totp_secret = data.secret
    await db.flush()


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_2fa(
    data: TwoFADisable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate 2FA after verifying a current code."""
    if not current_user.totp_secret:
        return
    if not pyotp.TOTP(current_user.totp_secret).verify(data.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Code ungültig")
    current_user.totp_secret = None
    await db.flush()
