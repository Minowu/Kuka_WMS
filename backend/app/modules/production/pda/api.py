"""REST API: PDA operator read endpoints (thin router)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production.pda import service as pda_service
from app.modules.production.pda.schema import (
    PdaCncStation,
    PdaModelItem,
    PdaRawMaterialSlot,
    PdaWashingSlot,
)

pda_router = APIRouter(tags=["Production - PDA Operator"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@pda_router.get(
    "/production/pda/models",
    response_model=list[PdaModelItem],
)
def get_pda_models(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách các Model sản phẩm khả dụng cho giao diện PDA."""
    return pda_service.list_pda_models(db)


@pda_router.get(
    "/production/pda/raw-materials",
    response_model=list[PdaRawMaterialSlot],
)
def get_pda_raw_materials(
    db: DbSession,
    user: CurrentUser,
):
    """Lấy trạng thái các vị trí tại Khu Nguyên Liệu (RAW-01..07) cho PDA."""
    return pda_service.list_pda_raw_materials(db, user)


@pda_router.get(
    "/production/pda/cnc-stations",
    response_model=list[PdaCncStation],
)
def get_pda_cnc_stations(
    db: DbSession,
    user: CurrentUser,
):
    """
    Lấy danh sách các trạm máy CNC (POS1 & POS2) cho PDA.
    Nếu là công nhân đã được gán user_locations, hệ thống sẽ lọc theo các vị trí được phân quyền.
    """
    return pda_service.list_pda_cnc_stations(db, user)


@pda_router.get(
    "/production/pda/washing-slots",
    response_model=list[PdaWashingSlot],
)
def get_pda_washing_slots(
    db: DbSession,
    user: CurrentUser,
):
    """Lấy danh sách 4 slot Khu Tẩy Rửa cho PDA."""
    return pda_service.list_pda_washing_slots(db, user)
