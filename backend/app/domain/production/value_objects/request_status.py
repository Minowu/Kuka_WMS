"""Value object: TransportRequest status."""

from enum import Enum


class RequestStatus(str, Enum):
    PENDING = "pending"
    QUEUED_FOR_CART = "queued_for_cart"
    QUEUED_FOR_SLOT = "queued_for_slot"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
