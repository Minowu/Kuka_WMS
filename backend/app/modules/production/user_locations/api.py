"""REST API: User location assignment (thin router)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production import user_location_service

user_locations_router = APIRouter(tags=["Production - User Locations"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@user_locations_router.get(
    "/production/users/{user_id}/locations",
    response_model=list[int],
)
def get_user_locations(
    user_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách ID các vị trí được phân quyền cho tài khoản công nhân."""
    return user_location_service.list_user_location_ids(db, user_id)


@user_locations_router.put(
    "/production/users/{user_id}/locations",
    response_model=list[int],
)
def update_user_locations(
    user_id: int,
    location_ids: list[int],
    db: DbSession,
    _user: CurrentUser,
):
    """Gán danh sách vị trí phân quyền cho tài khoản công nhân (1 user = 1 area duy nhất)."""
    try:
        return user_location_service.assign_user_locations(db, user_id, location_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
