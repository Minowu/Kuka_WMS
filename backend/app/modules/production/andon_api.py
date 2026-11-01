"""REST API endpoints for Production Andon TV displays."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.production import andon_service
from app.modules.production.andon_schema import AndonRawMaterialResponse

andon_router = APIRouter(tags=["Production - Andon TV"])

DbSession = Annotated[Session, Depends(get_db)]


@andon_router.get(
    "/production/andon/raw-material-queue",
    response_model=AndonRawMaterialResponse,
)
def get_andon_raw_material_queue(
    db: DbSession,
    warehouse_id: Optional[int] = Query(None, description="Lọc theo phân xưởng"),
):
    """
    Bảng điều độ Andon hiển thị nhu cầu cấp phôi nguyên liệu trên màn hình TV xưởng (Công khai, không yêu cầu đăng nhập):
    - Danh sách các yêu cầu phôi thô (target_stage_level = 0) đang chờ xếp hàng (TransportQueue.status == 'PENDING').
    - Trạng thái 7 ô cấp phôi tại bãi RAW_MATERIAL (ô trống vs ô có hàng).
    - Tự động biến mất khỏi danh sách khi xe phôi được nạp và gán cho máy CNC thành công.
    """
    return andon_service.get_raw_material_andon_queue(db, warehouse_id=warehouse_id)
