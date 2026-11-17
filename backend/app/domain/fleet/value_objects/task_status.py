"""Value object: Fleet task status."""

from enum import Enum


class FleetTaskStatus(str, Enum):
    CREATED = "created"
    PENDING_SUBMIT = "pending_submit"
    SUBMITTING = "submitting"
    SENT = "sent"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
