from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StationCatalogItem(BaseModel):
    id: int
    location_code: str
    location_label: Optional[str] = None
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    node_label: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MachineCatalogGroup(BaseModel):
    id: int
    machine_code: str
    machine_name: Optional[str] = None
    is_active: bool = True
    slots: list[StationCatalogItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StationCatalogResponse(BaseModel):
    raw_materials: list[StationCatalogItem] = Field(default_factory=list)
    washing_slots: list[StationCatalogItem] = Field(default_factory=list)
    empty_buffers: list[StationCatalogItem] = Field(default_factory=list)
    machines: list[MachineCatalogGroup] = Field(default_factory=list)


class MapAvailableNodeResponse(BaseModel):
    node_number: str
    node_label: str
    map_x: int
    map_y: int
    function_type: Optional[int] = None
    is_assigned: bool = False
    assigned_to: Optional[str] = None


class StationSlotCreateRequest(BaseModel):
    location_code: Optional[str] = Field(None, max_length=100)
    location_name: Optional[str] = Field(None, max_length=100)
    location_type: Optional[str] = Field(default="RAW_MATERIAL", max_length=30)
    position_index: Optional[int] = Field(None, ge=1)
    node_label: Optional[str] = Field(None, max_length=50)
    map_x: Optional[int] = None
    map_y: Optional[int] = None


class StationSlotUpdateRequest(BaseModel):
    location_name: Optional[str] = Field(None, max_length=100)
    position_index: Optional[int] = Field(None, ge=1)
    node_label: Optional[str] = Field(None, max_length=50)
    map_x: Optional[int] = None
    map_y: Optional[int] = None
