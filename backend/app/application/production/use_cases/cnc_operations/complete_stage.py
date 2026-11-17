"""Use case: Complete CNC machining stage — deep port orchestration."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from app.application.production.ports.services.active_cart_lookup import IActiveCartLookup
from app.application.production.ports.services.cart_stage_mutator import ICartStageMutator
from app.application.production.ports.services.complete_stage_support import (
    IMoveToWashRequestWriter,
    IStageEventNotifier,
    IUnitOfWork,
    IWaitingSlotQueue,
)
from app.application.production.ports.services.fleet_dispatcher import IFleetDispatcher
from app.application.production.ports.services.machine_stage_info import IMachineStageInfo
from app.application.production.ports.services.production_recorder import IProductionRecorder
from app.application.production.ports.services.queue_resolver import IQueueResolver
from app.application.production.ports.services.wash_slot_finder import IWashSlotFinder
from app.core.logger import bind_context, get_logger

logger = get_logger("wms.dispatch")


@dataclass
class CompleteStageRequest:
    container_code: Optional[str] = None
    location_id: Optional[int] = None
    operator_id: Optional[int] = None
    notes: Optional[str] = None


class CompleteStageUseCase:
    def __init__(
        self,
        cart_lookup: IActiveCartLookup,
        stage_info: IMachineStageInfo,
        cart_mutator: ICartStageMutator,
        recorder: IProductionRecorder,
        wash_finder: IWashSlotFinder,
        move_to_wash_writer: IMoveToWashRequestWriter,
        fleet_dispatcher: IFleetDispatcher,
        waiting_slot_queue: IWaitingSlotQueue,
        queue_resolver: IQueueResolver,
        notifier: IStageEventNotifier,
        uow: IUnitOfWork,
    ):
        self._cart_lookup = cart_lookup
        self._stage_info = stage_info
        self._cart_mutator = cart_mutator
        self._recorder = recorder
        self._wash_finder = wash_finder
        self._move_to_wash_writer = move_to_wash_writer
        self._fleet_dispatcher = fleet_dispatcher
        self._waiting_slot_queue = waiting_slot_queue
        self._queue_resolver = queue_resolver
        self._notifier = notifier
        self._uow = uow

    def execute(self, request: CompleteStageRequest) -> dict[str, Any]:
        if not request.container_code and not request.location_id:
            raise ValueError("Cần container_code hoặc location_id để hoàn thành công đoạn.")

        cart = self._cart_lookup.get_active_cart(
            container_code=request.container_code,
            location_id=request.location_id,
        )
        loc = self._cart_lookup.get_cart_location(cart.location_id)
        bind_context(
            container_code=cart.container_code,
            station_code=loc.location_code,
            machine_code=loc.machine_code,
        )

        info = self._stage_info.get_stage_info(loc.id, cart.item_id)
        if cart.current_stage_level >= info.target_stage:
            raise ValueError(
                f"Khay phôi '{cart.container_code}' đã hoàn thành công đoạn Level "
                f"{cart.current_stage_level} của máy này (yêu cầu Level {info.target_stage}). "
                f"Vui lòng chờ AMR vận chuyển sang công đoạn tiếp theo."
            )

        previous_stage = cart.current_stage_level
        completed_stage = info.target_stage
        self._cart_mutator.set_stage_level(cart.id, completed_stage)
        self._recorder.record_stage_completion(
            container_id=cart.id,
            container_code=cart.container_code,
            item_id=cart.item_id,
            stage_level=completed_stage,
            location_id=cart.location_id,
            machine_code=loc.machine_code,
            operator_id=request.operator_id,
            notes=request.notes,
        )

        if not info.is_final_cnc:
            self._uow.commit()
            self._queue_resolver.resolve_waiting_cart(stage_level=completed_stage)
            self._notifier.notify_stage_completed(
                location_ids=[loc.id],
                container_code=cart.container_code,
                operator_id=request.operator_id,
            )
            return {
                "container_code": cart.container_code,
                "completed_stage_level": completed_stage,
                "is_final_cnc_step": False,
                "action": "WIP_AVAILABLE_FOR_NEXT_STAGE",
            }

        req_code = f"REQ-{uuid4().hex[:8].upper()}"
        wash_slot = self._wash_finder.find_available_wash_slot()
        if wash_slot:
            logger.info(
                "Final CNC candidate decision: selected wash slot %s for cart %s",
                wash_slot.location_code,
                cart.container_code,
            )
            request_id = self._move_to_wash_writer.create_move_to_wash(
                request_code=req_code,
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=wash_slot.id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="pending",
                priority=5,
                created_by=request.operator_id,
            )
            bind_context(transport_request_id=request_id)
            try:
                self._fleet_dispatcher.lock_cart_and_dispatch(
                    transport_request_id=request_id,
                    cart_id=cart.id,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=wash_slot.id,
                )
            except Exception:
                self._cart_mutator.set_stage_level(cart.id, previous_stage)
                self._uow.commit()
                raise
            action = "DISPATCHED_TO_WASHING"
            request_code_out = req_code
        else:
            logger.info(
                "Final CNC candidate decision: no wash slot available for cart %s; queuing",
                cart.container_code,
            )
            request_id = self._move_to_wash_writer.create_move_to_wash(
                request_code=req_code,
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="queued_for_slot",
                priority=5,
                created_by=request.operator_id,
            )
            bind_context(transport_request_id=request_id)
            self._waiting_slot_queue.enqueue_waiting_slot(
                request_id=request_id, target_stage_level=99, priority=5
            )
            action = "QUEUED_FOR_WASHING_SLOT"
            request_code_out = req_code

        loc_ids = sorted(
            {int(x) for x in (loc.id, wash_slot.id if wash_slot else None) if x is not None}
        )
        self._uow.commit()
        if not wash_slot:
            self._notifier.notify_stage_queued_wash(
                location_ids=loc_ids,
                container_code=cart.container_code,
                operator_id=request.operator_id,
            )
        return {
            "container_code": cart.container_code,
            "completed_stage_level": completed_stage,
            "is_final_cnc_step": True,
            "action": action,
            "request_code": request_code_out,
        }
