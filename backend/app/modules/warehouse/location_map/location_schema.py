from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.warehouse.lot_number_utils import apply_lot_display_fields


class LocationCreate(BaseModel):
    location_code: str = Field(..., min_length=1, max_length=50)
    location_name: str = Field(..., min_length=1, max_length=100)
    bin_code: Optional[str] = Field(None, max_length=50)
    row: Optional[str] = Field(None, max_length=10)
    column: Optional[str] = Field(None, max_length=10)
    level: Optional[str] = Field(None, max_length=10)
    node_name: Optional[str] = Field(None, max_length=50)
    location_type: Optional[str] = "CNC_SLOT"
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    default_stage_level: Optional[int] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    warehouse_id: int
    zone_id: Optional[int] = None


class LocationUpdate(BaseModel):
    location_code: Optional[str] = Field(None, min_length=1, max_length=50)
    location_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bin_code: Optional[str] = Field(None, max_length=50)
    row: Optional[str] = Field(None, max_length=10)
    column: Optional[str] = Field(None, max_length=10)
    level: Optional[str] = Field(None, max_length=10)
    node_name: Optional[str] = Field(None, max_length=50)
    location_type: Optional[str] = None
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    default_stage_level: Optional[int] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    warehouse_id: Optional[int] = None
    zone_id: Optional[int] = None
    is_active: Optional[bool] = None


class LocationResponse(BaseModel):
    id: int
    location_code: str
    location_name: str
    bin_code: Optional[str] = None
    row: Optional[str] = None
    column: Optional[str] = None
    level: Optional[str] = None
    node_name: Optional[str] = None
    location_type: Optional[str] = None
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    default_stage_level: Optional[int] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    warehouse_id: int
    zone_id: Optional[int] = None
    is_active: bool
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LocationListResponse(BaseModel):
    items: list[LocationResponse]
    total: int
    page: int
    page_size: int


class LocationsByLogicResponse(BaseModel):
    items: list[LocationResponse]


class MapCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=255)
    warehouse_id: int
    zone_id: Optional[int] = None
    is_active: bool = Field(default=True)


class MapRemapEntry(BaseModel):
    """Move every reference of a bin that left the map onto a bin that is in it."""

    from_bin: str = Field(..., min_length=1, max_length=100)
    to_bin: str = Field(..., min_length=1, max_length=100)


class MapSyncMatchedItem(BaseModel):
    location_id: int
    bin_code: Optional[str] = None
    location_name: Optional[str] = None
    matched_by: str
    previous_location_code: Optional[str] = None
    location_code: str


class MapSyncCreatedItem(BaseModel):
    location_id: int
    bin_code: Optional[str] = None
    location_name: Optional[str] = None
    location_code: str


class MapSyncRemappedItem(BaseModel):
    from_location_id: int
    from_bin: Optional[str] = None
    to_location_id: int
    to_bin: Optional[str] = None
    moved: dict[str, int] = {}


class MapSyncRetiredItem(BaseModel):
    location_id: int
    bin_code: Optional[str] = None
    location_name: Optional[str] = None
    references: dict[str, int] = {}
    quantity: Optional[str] = None


class MapSyncFreedCode(BaseModel):
    location_id: int
    bin_code: Optional[str] = None
    released_location_code: str


class MapSyncUnnamedNode(BaseModel):
    location_code: str
    node_name: Optional[str] = None


class MapSyncCounts(BaseModel):
    matched: int
    created: int
    remapped: int
    retired: int
    blocked: int


class MapSyncResult(BaseModel):
    total_shelves: int
    matched: list[MapSyncMatchedItem] = []
    created: list[MapSyncCreatedItem] = []
    remapped: list[MapSyncRemappedItem] = []
    retired: list[MapSyncRetiredItem] = []
    blocked: list[MapSyncRetiredItem] = []
    freed_codes: list[MapSyncFreedCode] = []
    nodes_without_bin_code: list[MapSyncUnnamedNode] = []
    counts: MapSyncCounts
    warehouse_map_id: Optional[int] = None
    source: Optional[str] = None
    moved_cache_entries: Optional[int] = None


class MapDataResponse(BaseModel):
    width: int
    height: int
    node_keys: list[str] = Field(..., alias="nodeKeys")
    line_keys: list[str] = Field(..., alias="lineKeys")
    node_arr: list[list[Any]] = Field(..., alias="nodeArr")
    line_arr: list[list[Any]] = Field(..., alias="lineArr")
    type: Optional[str] = None
    x_attr_min: Optional[int] = Field(None, alias="xAttrMin")
    y_attr_min: Optional[int] = Field(None, alias="yAttrMin")
    floor_list: Optional[list[dict[str, Any]]] = Field(None, alias="floorList")
    node_list: Optional[list[dict[str, Any]]] = Field(None, alias="nodeList")
    edge_list: Optional[list[dict[str, Any]]] = Field(None, alias="edgeList")
    map_format: Optional[str] = Field("legacy", alias="mapFormat")
    model_config = ConfigDict(populate_by_name=True)


class ZoneMapLayoutNode(BaseModel):
    id: int
    location_code: str
    location_name: Optional[str] = None
    bin_code: Optional[str] = None
    row: Optional[str] = None
    column: Optional[str] = None
    level: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None


class ZoneMapLayoutResponse(BaseModel):
    zone_id: int
    warehouse_id: int
    nodes: list[ZoneMapLayoutNode]



class MapLocationStockItem(BaseModel):
    sku: str
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    quantity: str

    @model_validator(mode="after")
    def set_lot_display(self) -> "MapLocationStockItem":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class MapLocationItem(BaseModel):
    id: int
    location_code: str
    location_name: Optional[str] = None
    bin_code: Optional[str] = None
    row: Optional[str] = None
    column: Optional[str] = None
    level: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    status: str
    item_stock: list[MapLocationStockItem] = []


class LocationsForMapResponse(BaseModel):
    warehouse_id: int
    location_codes: list[str]
    locations: list[MapLocationItem]


class LocationDetailStockItem(BaseModel):
    id: int
    item_id: int
    sku: str
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: str
    status: str

    @model_validator(mode="after")
    def set_lot_display(self) -> "LocationDetailStockItem":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class LocationDetailSummary(BaseModel):
    item_stock_count: int
    total_quantity: str


class LocationDetailResponse(BaseModel):
    location: LocationResponse
    item_stock: list[LocationDetailStockItem]
    summary: LocationDetailSummary


class LocationQrPrintRequest(BaseModel):
    location_ids: list[int] = Field(..., min_length=1)
    warehouse_id: Optional[int] = None


class LocationQrPrintResponse(BaseModel):
    html: str
    quantity: int
    page_count: int
    qr_ids: list[str]
