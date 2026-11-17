"""Infrastructure: IDispatchGateway → dispatch_service facade."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.services.dispatch_gateway import IDispatchGateway
from app.modules.production.dispatch_service import dispatch_service


class DispatchServiceGateway(IDispatchGateway):
    def __init__(self, db: Session):
        self._db = db

    def register_rack_at_raw_material(self, **kwargs: Any) -> dict[str, Any]:
        return dispatch_service.register_rack_at_raw_material(db=self._db, **kwargs)

    def call_material_to_cnc(self, **kwargs: Any) -> Any:
        return dispatch_service.call_material_to_cnc(db=self._db, **kwargs)

    def complete_machining_stage(self, **kwargs: Any) -> dict[str, Any]:
        return dispatch_service.complete_machining_stage(db=self._db, **kwargs)

    def complete_washing_and_return_empty_cart(self, **kwargs: Any) -> Any:
        return dispatch_service.complete_washing_and_return_empty_cart(db=self._db, **kwargs)

    def receive_task_status(self, payload: dict[str, Any]) -> Any:
        return dispatch_service.receive_task_status(self._db, payload)
