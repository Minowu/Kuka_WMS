"""Pydantic schemas for Production Andon TV displays."""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class AndonRawMaterialDemand(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    request_code: str
    model_code: str
    model_name: str
    machine_code: str
    machine_name: str
    position_index: Optional[int] = None
    destination_location_code: str
    called_at: str
    priority: int = 10


class AndonRawSlotStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    location_id: int
    location_code: str
    name: str
    position_index: Optional[int] = None
    has_cart: bool
    cart_code: Optional[str] = None
    model_code: Optional[str] = None
    model_name: Optional[str] = None


class AndonRawMaterialResponse(BaseModel):
    demands: list[AndonRawMaterialDemand]
    raw_slots: list[AndonRawSlotStatus]
