"""Deprecated bridge — prefer CallMaterialUseCase via production_factory.

Kept for any leftover imports; forwards to the real use case.
"""

from sqlalchemy.orm import Session

from app.application.production.ports.services.call_material_gateway import (
    CallMaterialCommand,
    CallMaterialResult,
    ICallMaterialGateway,
)
from app.application.production.use_cases.cnc_operations.call_material import (
    CallMaterialRequest,
)
from app.infrastructure.di.production_factory import get_call_material_use_case


class DispatchServiceCallMaterialGateway(ICallMaterialGateway):
    def __init__(self, db: Session):
        self._db = db

    def execute(self, command: CallMaterialCommand) -> CallMaterialResult:
        result = get_call_material_use_case(self._db).execute(
            CallMaterialRequest(
                destination_location_id=command.destination_location_id,
                item_id=command.item_id,
                operator_id=command.created_by,
                priority=command.priority,
                required_stage_level=command.required_stage_level,
            )
        )
        return CallMaterialResult(
            id=result.request_id,
            request_code=result.request_code,
            status=result.status,
            container_id=result.container_id,
            destination_location_id=result.destination_location_id,
            required_stage_level=result.required_stage_level,
        )
