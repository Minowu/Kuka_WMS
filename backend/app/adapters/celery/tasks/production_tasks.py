"""Celery production tasks adapter — re-export from modules (Strangler)."""

from app.modules.production.production_celery_task import (  # noqa: F401
    enqueue_fleet_submit,
    persist_task_status,
    scan_transport_queue,
    submit_fleet_task,
    sweep_fleet_tasks,
)

__all__ = [
    "enqueue_fleet_submit",
    "persist_task_status",
    "scan_transport_queue",
    "submit_fleet_task",
    "sweep_fleet_tasks",
]
