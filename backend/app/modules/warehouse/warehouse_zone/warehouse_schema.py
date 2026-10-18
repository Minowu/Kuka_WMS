from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class WarehouseUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class WarehouseResponse(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WarehouseListResponse(BaseModel):
    items: list[WarehouseResponse]
    total: int
    page: int
    page_size: int
