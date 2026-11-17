"""Domain entity: TransportRequest (pure, no ORM)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.domain.production.value_objects.request_status import RequestStatus


@dataclass
class TransportRequest:
    id: Optional[int]
    request_code: str
    request_type: str
    item_id: Optional[int]
    destination_location_id: Optional[int]
    required_stage_level: int
    status: str
    priority: int = 10
    source_location_id: Optional[int] = None
    container_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    @staticmethod
    def create_call_cnc(
        *,
        item_id: int,
        destination_location_id: int,
        required_stage_level: int,
        created_by: Optional[int] = None,
        priority: int = 10,
    ) -> "TransportRequest":
        return TransportRequest(
            id=None,
            request_code=f"REQ-{uuid4().hex[:8].upper()}",
            request_type="CALL_CNC",
            item_id=item_id,
            destination_location_id=destination_location_id,
            required_stage_level=required_stage_level,
            status=RequestStatus.PENDING.value,
            priority=priority,
            created_by=created_by,
        )

    def mark_queued_for_cart(self) -> None:
        self.status = RequestStatus.QUEUED_FOR_CART.value

    def mark_in_progress(self) -> None:
        self.status = RequestStatus.IN_PROGRESS.value

    def is_ready_to_dispatch(self) -> bool:
        return self.status == RequestStatus.PENDING.value and self.container_id is not None
