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

from app.config import settings

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
    totp_enabled: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    payload = verify_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungültig",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    if form_data.username != settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
        )
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kein Admin-Passwort konfiguriert",
        )
    if not verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
        )

    # 2FA — if TOTP_SECRET is configured, require code in scope field
    if settings.TOTP_SECRET:
        totp_code = (form_data.scopes[0] if form_data.scopes else "").strip()
        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA-Code erforderlich",
            )
        totp = pyotp.TOTP(settings.TOTP_SECRET)
        if not totp.verify(totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA-Code ungültig",
            )

    access_token = create_access_token(data={"sub": form_data.username})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserInfo)
async def me(current_user: str = Depends(get_current_user)) -> UserInfo:
    return UserInfo(username=current_user, totp_enabled=bool(settings.TOTP_SECRET))


@router.get("/2fa/setup")
async def setup_2fa(current_user: str = Depends(get_current_user)) -> Response:
    """Generates a new TOTP secret + QR code as PNG.
    NOTE: Save the secret to TOTP_SECRET in .env to activate 2FA.
    """
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=settings.ADMIN_USERNAME,
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
            "X-TOTP-Hint": "Save this secret to TOTP_SECRET in .env to activate 2FA",
        },
    )
