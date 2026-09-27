import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from app.core.config import get_settings
from app.db.models import AuditLog, User, UserRole
from app.db.session import get_async_session
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# ---------------------------------------------------------------------------
# Password hashing.
#
# This module used passlib's CryptContext(schemes=["bcrypt"]). passlib 1.7.4
# probes `bcrypt.__about__.__version__` (removed in bcrypt>=4.1) and then runs a
# >72-byte "wraparound bug" detection hash. bcrypt>=4.1 *raises* on that input
# instead of truncating, so every single call to get_password_hash() blew up
# with:
#     ValueError: password cannot be longer than 72 bytes
# i.e. /auth/register always 500'd and no user could ever be created.
# passlib is unmaintained (last release 2020); we call bcrypt directly. The
# hash format ($2b$) is unchanged, so any hashes created before this fix still
# verify.
# ---------------------------------------------------------------------------
BCRYPT_ROUNDS = 12
BCRYPT_MAX_BYTES = 72

#: Single source of truth for the JWT lifetime (documented as 30 minutes).
ACCESS_TOKEN_TTL_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: str | None = None
    role: str | None = None
    permissions: list[str] = []


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole = UserRole.TRADER


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


def _normalize_secret(plain_password: str) -> bytes:
    """UTF-8 encode and clamp to bcrypt's 72-byte block.

    bcrypt silently ignores everything past byte 72; bcrypt>=4.1 raises
    instead. Truncating explicitly keeps behaviour deterministic across
    versions. UTF-8 is used (not latin-1) so multi-byte passwords are handled
    consistently.
    """
    return plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_normalize_secret(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        # Malformed/unusable stored hash — never crash the login path.
        logger.warning("Password verification failed against stored hash: %s", exc)
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        _normalize_secret(password),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    # `iat` was missing, so a stolen token's age could not be determined and
    # rotation/revocation windows had nothing to anchor on.
    to_encode.setdefault("iat", now)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.API_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=["HS256"])
        raw_sub = payload.get("sub")
        if raw_sub is None:
            raise credentials_exception
        # `sub` is issued as str(user.id) — coerce back to int before hitting
        # the integer primary key, otherwise the DB driver rejects the lookup.
        user_id = int(raw_sub)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception from None

    # TokenData is validated here so a malformed `role`/`permissions` claim is
    # rejected before it reaches any authorisation decision.
    TokenData(sub=str(user_id), role=payload.get("role"), permissions=payload.get("permissions", []))

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(*allowed_roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker


def require_permission(*permissions: str):
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # In a real implementation, check user permissions from token or DB
        # For now, superusers have all permissions
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return permission_checker


async def create_audit_log(
    db: AsyncSession,
    action: str,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=str(details) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        error_message=error_message,
    )
    db.add(audit_log)
    await db.commit()


def get_client_info(request: Request) -> dict[str, str | None]:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }