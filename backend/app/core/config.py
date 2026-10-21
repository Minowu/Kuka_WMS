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
    #App
    app_name: str = "Warehouse Management System"
    debug: bool = False

    #Database
    database_url: str = "postgresql://postgres:thado123@localhost:5432/masan_wms"

    #JWT
    secret_key: str = "no_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 10080

    # KUKA Fleet Manager (Real KUKA ICS Protocol)
    kuka_base_url: str = "http://192.168.1.71:10870/interfaces/api"
    kuka_access_token: str = ""
    kuka_org_id: str = "KUKA011021"
    kuka_container_model_code: str = "1001"
    kuka_robot_type: str = "LIFT"
    kuka_mission_type: str = "RACK_MOVE"
    kuka_http_timeout_seconds: float = 5.0
    kuka_submit_max_retries: int = 3
    # Backward compatibility alias
    ics_base_url: str = "http://192.168.1.71:10870/interfaces/api"

    # Warehouses using manual (full-form) print templates — JSON array or comma list, e.g. [2]
    manual_warehouse_ids: list[int] = []

    # Redis (cache)
    redis_url: str = "redis://192.168.50.200:6379/0"
    redis_cache_ttl: int = 300
    redis_key_prefix: str = "wms"

    # Redis Celery
    celery_broker_url: str = "redis://192.168.50.200:6379/1"
    celery_broker_result_url: str = "redis://192.168.50.200:6379/2"

    # Expired configuration
    manual_expired_days: int = 60
    auto_expired_days: int = 30

    @field_validator("manual_warehouse_ids", mode="before")
    @classmethod
    def parse_manual_warehouse_ids(cls, value: object) -> list[int]:
        return _parse_int_id_list(value)

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        case_sensitive = False

settings = Settings()
