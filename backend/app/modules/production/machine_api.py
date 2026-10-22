from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production import machine_service
from app.modules.production.machine_schema import (
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
)

machine_router = APIRouter(tags=["Production - Machines"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@machine_router.get(
    "/production/machines",
    response_model=list[AvailableMachineResponse],
)
def list_available_machines(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách các máy CNC hiện có từ bảng Machine (3NF) để cấu hình bước quy trình."""
    return machine_service.list_available_machines(db)


@machine_router.post(
    "/production/machines",
    response_model=AvailableMachineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_machine(
    payload: MachineCreateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    """Tạo máy CNC mới trên xưởng và tự động khởi tạo 1..3 vị trí đỗ."""
    try:
        return machine_service.create_machine(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@machine_router.get(
    "/production/machines/{machine_id}",
    response_model=AvailableMachineResponse,
)
def get_machine(
    machine_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy chi tiết thông tin và danh sách slot đỗ của máy CNC."""
    try:
        return machine_service.get_machine(db, machine_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@machine_router.put(
    "/production/machines/{machine_id}",
    response_model=AvailableMachineResponse,
)
def update_machine(
    machine_id: int,
    payload: MachineUpdateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    """Cập nhật thông tin máy CNC và danh sách 1..3 slot đỗ."""
    try:
        return machine_service.update_machine(db, machine_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@machine_router.delete(
    "/production/machines/{machine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_machine(
    machine_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Xóa / vô hiệu hóa máy CNC."""
    try:
        machine_service.delete_machine(db, machine_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

