
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core.config import settings
from app.core.logger import setup_logger


from typing import Any
from celery import Task

CELERY_LOGIC_TIMEOUT = 120

QUEUE_LOGIC = "logic"
QUEUE_STATUS = "status"

celery_app = Celery(
    "wms",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_result_url,
    include=[
        "app.modules.warehouse.notificcation.notification_celery_task",
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

    result_expires=3600,             
    task_track_started=True,         

    task_default_queue=QUEUE_LOGIC,
    task_queues={
        QUEUE_LOGIC: {},
        QUEUE_STATUS: {},
    },
    task_routes={
        "notification.*": {"queue": QUEUE_LOGIC},
        "robot.*": {"queue": QUEUE_STATUS},
    },
    beat_schedule={},
)


@worker_process_init.connect
def init_worker_logging(**_kwargs):
    """Worker không import main.py → phải setup logger riêng."""
    setup_logger(
        name="main",
        log_level="INFO",
        service_name="celery",
        log_dir="logs/celery",
    )

def run_logic_task(task: Task, /, **kwargs: Any) -> Any:
    if settings.debug:  
        return task.apply(kwargs=kwargs).get(propagate=True)
    return task.apply_async(kwargs=kwargs).get(
        timeout=CELERY_LOGIC_TIMEOUT,
        propagate=True,
    )