"""REST API endpoints for Transport Request & Queue Management (Admin)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production import request_service
from app.modules.production.request_schema import (
    TransportRequestCancelResponse,
    TransportRequestManagementItem,
)

request_router = APIRouter(tags=["Production - Transport Requests & Queue"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _ensure_admin(user: User) -> None:
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Admin mới có quyền hủy yêu cầu vận chuyển.",
        )


@request_router.get(
    "/production/requests",
    response_model=list[TransportRequestManagementItem],
)
def list_production_transport_requests(
    db: DbSession,
    _user: CurrentUser,
    include_history: bool = Query(False, description="Hiển thị cả các yêu cầu đã hoàn thành / đã hủy"),
    search: Optional[str] = Query(None, description="Tìm theo mã lệnh, máy CNC, vị trí, mã rack, model..."),
):
    """Lấy danh sách các yêu cầu vận chuyển / gọi phôi đang hoạt động trên xưởng."""
    return request_service.list_transport_requests(
        db=db,
        include_history=include_history,
        search=search,
    )


@request_router.post(
    "/production/requests/{request_id}/cancel",
    response_model=TransportRequestCancelResponse,
)
@request_router.delete(
    "/production/requests/{request_id}",
    response_model=TransportRequestCancelResponse,
)
def cancel_production_transport_request(
    request_id: int,
    db: DbSession,
    user: CurrentUser,
):
    """
    Admin chủ động hủy yêu cầu vận chuyển / gọi phôi (hủy hàng đợi, gửi missionCancel nếu AMR đang chạy,
    mở khóa Rack và phát sự kiện WebSocket làm mới tức thì màn hình PDA của Operator).
    """
    _ensure_admin(user)
    try:
        return request_service.cancel_transport_request_by_admin(
            db=db,
            request_id=request_id,
            operator_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
