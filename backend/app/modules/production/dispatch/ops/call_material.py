"""Call material — delegates to Clean Architecture use case (single source of truth)."""

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.production.production_models import TransportRequest


def call_material_to_cnc(
    core,
    db: Session,
    destination_location_id: int,
    item_id: Optional[int] = None,
    required_stage_level: Optional[int] = None,
    created_by: Optional[int] = None,
    priority: int = 10,
) -> TransportRequest:
    """Operator at CNC station calls material (1-Touch pull)."""
    if item_id is None:
        raise ValueError("Vui lòng chọn Model sản phẩm cần gọi đến vị trí đích.")

    # Lazy imports avoid circular: dispatch → ops → factory → dispatch_service
    from app.application.production.use_cases.cnc_operations.call_material import (
        CallMaterialRequest,
    )
    from app.infrastructure.di.production_factory import build_call_material_use_case

    use_case = build_call_material_use_case(
        db,
        selector=core.selector,
        queue_service=core.queue_service,
        lock_fn=core.lock_cart_and_dispatch_fleet_task,
    )
    result = use_case.execute(
        CallMaterialRequest(
            destination_location_id=destination_location_id,
            item_id=item_id,
            operator_id=created_by,
            priority=priority,
            required_stage_level=required_stage_level,
        )
    )
    orm = (
        db.query(TransportRequest)
        .filter(TransportRequest.id == result.request_id)
        .first()
    )
    if not orm:
        raise ValueError(f"TransportRequest id={result.request_id} missing after call_material")
    return orm
