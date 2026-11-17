"""Domain entity: TransportQueue entry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TransportQueueEntry:
    id: Optional[int]
    request_id: int
    queue_type: str  # WAITING_CART | WAITING_SLOT
    status: str = "PENDING"
    target_stage_level: Optional[int] = None
    priority: int = 10
    retry_count: int = 0
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def mark_resolved(self, when: Optional[datetime] = None) -> None:
        self.status = "RESOLVED"
        self.resolved_at = when or datetime.utcnow()
