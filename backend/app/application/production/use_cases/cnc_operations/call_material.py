"""Use case: Call material for CNC machine (1-touch pull) — real orchestration."""

from dataclasses import dataclass
from typing import Optional

from app.application.production.ports.repositories.transport_request_repository import (
    ITransportRequestRepository,
)
from app.application.production.ports.services.cart_finder import ICartFinder
from app.application.production.ports.services.fleet_dispatcher import IFleetDispatcher
from app.application.production.ports.services.floor_notifier import IFloorNotifier
from app.application.production.ports.services.location_guard import ILocationGuard
from app.application.production.ports.services.stage_resolver import IStageResolver
from app.application.production.ports.services.transport_queue import ITransportQueue
from app.application.production.ports.services.unit_of_work_port import ICallMaterialUnitOfWork
from app.core.logger import bind_context, get_logger
from app.domain.production.entities.transport_request import TransportRequest
from app.domain.production.value_objects.request_status import RequestStatus

logger = get_logger("wms.dispatch")


@dataclass
class CallMaterialRequest:
    destination_location_id: int
    item_id: int
    operator_id: Optional[int] = None
    priority: int = 10
    required_stage_level: Optional[int] = None


@dataclass
class CallMaterialResponse:
    request_id: int
    request_code: str
    status: str
    container_id: Optional[int]
    destination_location_id: Optional[int]
    required_stage_level: Optional[int]


class CallMaterialUseCase:
    """
    Application use case for CNC call-material.

    Orchestrates ports only — no direct SQLAlchemy / DispatchCore dependency.
    """

    def __init__(
        self,
        location_guard: ILocationGuard,
        stage_resolver: IStageResolver,
        cart_finder: ICartFinder,
        transport_request_repo: ITransportRequestRepository,
        transport_queue: ITransportQueue,
        fleet_dispatcher: IFleetDispatcher,
        floor_notifier: IFloorNotifier,
        uow: ICallMaterialUnitOfWork,
    ):
        self._location_guard = location_guard
        self._stage_resolver = stage_resolver
        self._cart_finder = cart_finder
        self._transport_request_repo = transport_request_repo
        self._transport_queue = transport_queue
        self._fleet_dispatcher = fleet_dispatcher
        self._floor_notifier = floor_notifier
        self._uow = uow

    def execute(self, request: CallMaterialRequest) -> CallMaterialResponse:
        if not request.destination_location_id:
            raise ValueError("Thiếu vị trí đích (destination_location_id).")
        if request.item_id is None:
            raise ValueError("Vui lòng chọn Model sản phẩm cần gọi.")

        dest = self._location_guard.get_active_destination(request.destination_location_id)
        self._location_guard.ensure_location_free(dest.id, dest.location_code)

        required_stage = request.required_stage_level
        if required_stage is None:
            required_stage = self._stage_resolver.resolve_required_stage(dest.id, request.item_id)

        bind_context(station_code=dest.location_code, machine_code=dest.machine_code)
        logger.info(
            "call_material input: destination_location_id=%s (%s), machine=%s, item_id=%s, "
            "required_stage_level=%s, priority=%s, created_by=%s",
            dest.id,
            dest.location_code,
            dest.machine_code,
            request.item_id,
            required_stage,
            request.priority,
            request.operator_id,
        )

        transport_req = TransportRequest.create_call_cnc(
            item_id=request.item_id,
            destination_location_id=dest.id,
            required_stage_level=required_stage,
            created_by=request.operator_id,
            priority=request.priority,
        )
        transport_req = self._transport_request_repo.save(transport_req)
        bind_context(transport_request_id=transport_req.id)
        logger.info(
            "TransportRequest %s: %s -> %s (reason: %s)",
            transport_req.id,
            "new",
            RequestStatus.PENDING.value,
            f"Material requested for station {dest.location_code} (item_id={request.item_id})",
        )

        cart = self._cart_finder.find_fifo_available_cart(
            item_id=request.item_id,
            stage_level=required_stage,
            destination_location_id=dest.id,
        )

        if cart:
            logger.info(
                "call_material candidate decision: selected cart %s at location_id=%s for destination %s",
                cart.container_code,
                cart.location_id,
                dest.location_code,
            )
            self._fleet_dispatcher.lock_cart_and_dispatch(
                transport_request_id=transport_req.id,
                cart_id=cart.id,
                pickup_location_id=cart.location_id,
                dropoff_location_id=dest.id,
            )
        else:
            logger.info(
                "call_material candidate decision: no eligible cart for item_id=%s, stage_level=%s; queuing",
                request.item_id,
                required_stage,
            )
            transport_req.mark_queued_for_cart()
            transport_req = self._transport_request_repo.save(transport_req)
            self._transport_queue.enqueue_waiting_cart(
                request_id=transport_req.id,
                target_stage_level=required_stage,
                priority=request.priority,
            )

        self._uow.commit()
        saved = self._uow.refresh_transport_request(transport_req.id)

        if not cart:
            loc_ids = sorted(
                {
                    int(lid)
                    for lid in (dest.id, saved.source_location_id)
                    if lid is not None
                }
            )
            self._floor_notifier.notify_call_material_queued(
                request_code=saved.request_code,
                location_ids=loc_ids,
                operator_id=request.operator_id,
            )

        return CallMaterialResponse(
            request_id=saved.id,
            request_code=saved.request_code,
            status=saved.status,
            container_id=saved.container_id,
            destination_location_id=saved.destination_location_id,
            required_stage_level=saved.required_stage_level,
        )
