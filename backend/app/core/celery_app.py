
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core.config import settings
from app.core.logger import configure_logging
from app.core.observability import install_celery_signals


from typing import Any
from celery import Task

CELERY_LOGIC_TIMEOUT = 120

QUEUE_LOGIC = "logic"
QUEUE_STATUS = "status"
QUEUE_FLEET = "fleet"

celery_app = Celery(
    "wms",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_result_url,
    include=[
        "app.modules.production.production_celery_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="Asia/Ho_Chi_Minh",
    enable_utc=False,

    task_acks_late=True,             
    worker_prefetch_multiplier=1,    
    task_reject_on_worker_lost=True, 
    broker_connection_retry_on_startup=True,

    task_time_limit=300,              
    task_soft_time_limit=270,        

    task_ignore_result=True,
    result_expires=3600,             
    task_track_started=True,         

    task_default_queue=QUEUE_LOGIC,
    task_queues={
        QUEUE_LOGIC: {},
        QUEUE_STATUS: {},
        QUEUE_FLEET: {},
    },
    task_routes={
        "production.submit_fleet_task": {"queue": QUEUE_FLEET},
        "production.sweep_fleet_tasks": {"queue": QUEUE_FLEET},
        "production.*": {"queue": QUEUE_LOGIC},
        "robot.*": {"queue": QUEUE_STATUS},
    },
    beat_schedule={
        "always-scan-transport-queue": {
            "task": "production.scan_transport_queue",
            "schedule": 5.0,
        },
        "sweep-fleet-tasks": {
            "task": "production.sweep_fleet_tasks",
            "schedule": 15.0,
        },
    },
)


@worker_process_init.connect
def init_worker_logging(**_kwargs):
    """Worker không import main.py → setup logger và gán vai trò DB Celery."""
    import os
    os.environ["WMS_DB_ROLE"] = "celery"
    configure_logging()


install_celery_signals()