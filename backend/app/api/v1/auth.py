from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_user,
    create_audit_log,
    get_client_info,
    require_role,
    get_password_hash,
    get_user_by_email,
    get_user_by_id,
    User,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserRole,
    Token,
)
from app.db.session import get_async_session

router = APIRouter(tags=["Authentication & Authorization"])


@router.post("/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_session),
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        client_info = get_client_info(request)
        await create_audit_log(
            db,
            action="login_failed",
            user_id=None,
            resource_type="auth",
            details={"email": form_data.username},
            ip_address=client_info["ip"],
            user_agent=client_info["user_agent"],
            status="failure",
            error_message="Invalid credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "permissions": []},
        expires_delta=access_token_expires,
    )

    user.last_login = datetime.utcnow()
    await db.commit()

    client_info = get_client_info(request)
    await create_audit_log(
        db,
        action="login_success",
        user_id=user.id,
        resource_type="auth",
        ip_address=client_info["ip"],
        user_agent=client_info["user_agent"],
    )

    return Token(access_token=access_token, token_type="bearer", expires_in=1800)


@router.post("/auth/register", response_model=UserResponse)
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    client_info = get_client_info(request)
    await create_audit_log(
        db,
        action="user_created",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "role": user.role.value},
        ip_address=client_info["ip"],
        user_agent=client_info["user_agent"],
    )

    return UserResponse.model_validate(user)


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/auth/me", response_model=UserResponse)
async def update_current_user(
    request: Request,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.is_active is not None and current_user.is_superuser:
        current_user.is_active = user_update.is_active

    await db.commit()
    await db.refresh(current_user)

    client_info = get_client_info(request)
    await create_audit_log(
        db,
        action="user_updated",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details=user_update.model_dump(exclude_unset=True),
        ip_address=client_info["ip"],
        user_agent=client_info["user_agent"],
    )

    return UserResponse.model_validate(current_user)


@router.get("/auth/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[UserResponse]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/auth/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/auth/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    await db.commit()
    await db.refresh(user)

    client_info = get_client_info(request)
    await create_audit_log(
        db,
        action="user_updated_admin",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        details=user_update.model_dump(exclude_unset=True),
        ip_address=client_info["ip"],
        user_agent=client_info["user_agent"],
    )

    return UserResponse.model_validate(user)


@router.delete("/auth/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    client_info = get_client_info(request)
    await create_audit_log(
        db,
        action="user_deleted",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(user_id),
        details={"email": user.email},
        ip_address=client_info["ip"],
        user_agent=client_info["user_agent"],
    )

    return {"status": "deleted", "user_id": user_id}