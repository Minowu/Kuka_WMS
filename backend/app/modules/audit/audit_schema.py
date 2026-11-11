from datetime import datetime
from ipaddress import ip_address
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

AuditEventType = Literal["LOGIN", "LOGOUT", "PERMISSION_DENIED", "TOKEN_INVALID"]
LogResult = Literal["SUCCESS", "FAILED"]
DeviceType = Literal["pda", "tv", "desktop"]


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    result: str
    failure_reason: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    device_name: Optional[str] = None
    request_id: Optional[str] = None
    path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class ActionLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: Optional[str] = None
    method: str
    route_template: Optional[str] = None
    path: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status_code: int
    result: str
    error_message: Optional[str] = None
    payload: Optional[Any] = None
    query_params: Optional[Any] = None
    duration_ms: Optional[int] = None
    ip: Optional[str] = None
    device_type: Optional[str] = None
    device_name: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionLogListResponse(BaseModel):
    items: list[ActionLogResponse]
    total: int
    page: int
    page_size: int


class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    device_type: DeviceType = "pda"
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class DeviceCreate(DeviceBase):
    ip_address: str = Field(..., max_length=45)

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        return str(ip_address(value.strip()))


class DeviceUpdate(BaseModel):
    ip_address: Optional[str] = Field(None, max_length=45)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    device_type: Optional[DeviceType] = None
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, value: Optional[str]) -> Optional[str]:
        return str(ip_address(value.strip())) if value else value


class DeviceResponse(BaseModel):
    id: int
    ip_address: str
    name: str
    device_type: str
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
