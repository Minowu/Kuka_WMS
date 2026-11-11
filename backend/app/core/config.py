import json
import os

from pydantic_settings import BaseSettings
from pydantic import field_validator

def _parse_int_id_list(raw: object) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [int(value) for value in raw if str(value).strip().isdigit()]
    text = str(raw).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [int(value) for value in parsed if str(value).strip().lstrip("-").isdigit()]
    except json.JSONDecodeError:
        pass
    return [
        int(part)
        for part in text.split(",")
        if part.strip().lstrip("-").isdigit()
    ]


class Settings(BaseSettings):
    # App
    app_name: str = "KUKA Warehouse Management System"
    debug: bool = False

    # Database (PostgreSQL 16)
    database_url: str = "postgresql://postgres:thado123@localhost:5433/kuka"
    db_role: str = "backend"  # "backend" | "celery"
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 10
    db_pool_recycle: int = 1800

    # JWT Authentication Security
    secret_key: str = "kuka_wms_default_secret_key_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 10080

    # KUKA Fleet Manager (Real KUKA ICS Protocol)
    kuka_base_url: str = "http://192.168.1.71:10870/interfaces/api"
    kuka_access_token: str = "1726185d4d777843ff5eb65171f11b12f9fb364ef2bd2d7c265e36e3389f18c1"
    kuka_org_id: str = "TDS_KUKA_ORG"
    kuka_container_model_code: str = "1001"
    kuka_robot_type: str = "LIFT"
    kuka_mission_type: str = "RACK_MOVE"
    kuka_http_timeout_seconds: float = 8.0
    kuka_submit_max_retries: int = 3

    # Warehouses using manual (full-form) print templates — JSON array or comma list, e.g. [2]
    manual_warehouse_ids: list[int] = []

    # Redis (cache)
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300
    redis_key_prefix: str = "wms"

    # Redis Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_broker_result_url: str = "redis://localhost:6379/2"

    # Audit / Action log
    # Reverse proxies (nginx container) allowed to set X-Real-IP / X-Forwarded-For — comma list of CIDR
    trusted_proxy_cidrs: str = "127.0.0.1/32,172.16.0.0/12"
    audit_log_retention_days: int = 180
    action_log_retention_days: int = 90

    @field_validator("manual_warehouse_ids", mode="before")
    @classmethod
    def parse_manual_warehouse_ids(cls, value: object) -> list[int]:
        return _parse_int_id_list(value)

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        case_sensitive = False

settings = Settings()
