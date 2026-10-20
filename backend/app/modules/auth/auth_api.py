from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.auth.auth_model import User, Role
from app.modules.auth.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RoleBrief,
    TokenResponse,
    UserCreate,
    UserSignupResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
    StaffUsernamesResponse,
)
from app.modules.auth import auth_service
from app.modules.auth.auth_access import user_to_response
from app.core.logger import get_logger

logger = get_logger(name="main")
router = APIRouter(tags=["Auth"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _user_to_response(user: User, db: Session) -> UserResponse:
    return user_to_response(db, user)

@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: DbSession):
    try:
        logger.info(f"Successfully logged in user {body.username}")
        return auth_service.login(db, body)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/auth/refresh", response_model=RefreshTokenResponse)
def refresh_token(body: RefreshTokenRequest, db: DbSession):
    access_token = auth_service.refresh_access_token(db, body.refresh_token)
    if not access_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return RefreshTokenResponse(access_token=access_token)

@router.post(
    "/auth/signup",
    response_model=UserSignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(body: UserCreate, db: DbSession):
    try:
        return auth_service.sign_up(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: CurrentUser, db: DbSession):
    return _user_to_response(current_user, db)


@router.get(
    "/users/staff-usernames",
    response_model=StaffUsernamesResponse,
)
def list_staff_usernames(_current_user: CurrentUser, db: DbSession):
    """Username list for tablet assign-by picker (any logged-in user)."""
    return auth_service.list_staff_usernames(db)


@router.get("/roles", response_model=list[RoleBrief])
def list_roles(db: DbSession, _user: CurrentUser):
    """Lấy danh sách các vai trò (roles) trong hệ thống."""
    return db.query(Role).order_by(Role.id.asc()).all()



@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def list_users(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return auth_service.list_users(db, page=page, page_size=page_size)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def get_user_by_id(user_id: int, db: DbSession):
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_response(user, db)


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:update"))],
)
def update_user(user_id: int, body: UserUpdate, db: DbSession):
    try:
        user = auth_service.update_user(db, user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_response(user, db)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:delete"))],
)
def delete_user(user_id: int, db: DbSession, current_user: CurrentUser):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    deleted = auth_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return None