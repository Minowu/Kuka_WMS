"""User ↔ Location assignment helpers (PDA access control)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import user_is_admin
from app.modules.auth.auth_model import User
from app.modules.production.dispatch.service import dispatch_service
from app.modules.production.production_models import UserLocation


def ensure_user_can_access_location(
    db: Session,
    user: User,
    location_id: int,
    action_desc: str,
) -> None:
    """Raise HTTP 403 if non-admin user is not assigned to the location."""
    if user_is_admin(user):
        return
    assigned = (
        db.query(UserLocation)
        .filter(UserLocation.user_id == user.id, UserLocation.location_id == location_id)
        .first()
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Bạn không có quyền thực hiện thao tác '{action_desc}' "
                f"tại trạm/vị trí này (ID={location_id})."
            ),
        )


def list_user_location_ids(db: Session, user_id: int) -> list[int]:
    return [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user_id).all()
    ]


def assign_user_locations(db: Session, user_id: int, location_ids: list[int]) -> list[int]:
    """Gán danh sách vị trí; raise ValueError nếu validate thất bại."""
    assigned = dispatch_service.assign_locations_to_user(
        db, user_id=user_id, location_ids=location_ids
    )
    return [ul.location_id for ul in assigned]
