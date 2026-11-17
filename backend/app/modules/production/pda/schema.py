"""Pydantic schemas for PDA operator endpoints."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PdaModelItem(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    standard_quantity_per_cart: int = 120

    model_config = ConfigDict(from_attributes=True)


class PdaRawMaterialSlot(BaseModel):
    id: str
    location_id: int
    name: str
    has_rack: bool
    current_rack_id: Optional[str] = None
    current_model: Optional[str] = None
    last_error: Optional[str] = None


class PdaCncStationRack(BaseModel):
    rack_id: str
    model: str
    level: int
    started_at: Optional[str] = None
    is_completed: bool = False
    is_locked: bool = False
    locked_by_mission: Optional[str] = None


class PdaCncSupportedModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    item_id: int
    model_code: str
    model_name: str
    stage_level: int
    stage_name: str
    input_stage_level: int


class PdaCncStation(BaseModel):
    id: str
    location_id: int
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    name: str
    assigned_stage_level: int
    stage_name: str
    is_final_step: bool = False
    status: str
    calling_model: Optional[str] = None
    calling_mission_code: Optional[str] = None
    current_rack: Optional[PdaCncStationRack] = None
    supported_models: list[PdaCncSupportedModel] = []
    last_error: Optional[str] = None


class PdaWashingSlotRack(BaseModel):
    rack_id: str
    model: str
    from_station: Optional[str] = None
    arrived_at: Optional[str] = None


class PdaWashingSlot(BaseModel):
    id: int
    location_id: int
    code: str
    name: str
    status: str
    current_rack: Optional[PdaWashingSlotRack] = None
    last_error: Optional[str] = None
