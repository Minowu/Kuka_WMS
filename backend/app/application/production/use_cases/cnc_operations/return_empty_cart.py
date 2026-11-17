"""Use case: Return empty cart from washing to buffer — deep port orchestration."""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from app.application.production.ports.services.cart_stage_mutator import ICartStageMutator
from app.application.production.ports.services.complete_stage_support import (
    IUnitOfWork,
    IWaitingSlotQueue,
)
from app.application.production.ports.services.fleet_dispatcher import IFleetDispatcher
from app.application.production.ports.services.queue_resolver import IQueueResolver
from app.application.production.ports.services.return_empty_support import (
    IEmptyBufferFinder,
    IReturnEmptyEventNotifier,
    IReturnEmptyRequestWriter,
    IWashCartLookup,
)
from app.core.logger import bind_context, get_logger
from app.domain.production.value_objects.rack_code import RackCode

logger = get_logger("wms.dispatch")


@dataclass
class ReturnEmptyCartRequest:
    container_code: str
    operator_id: Optional[int] = None


@dataclass
class ReturnEmptyCartResponse:
    id: int
    request_code: str
    status: str
    container_id: Optional[int]
    destination_location_id: Optional[int]


class ReturnEmptyCartUseCase:
    def __init__(
        self,
        wash_lookup: IWashCartLookup,
        buffer_finder: IEmptyBufferFinder,
        cart_mutator: ICartStageMutator,
        request_writer: IReturnEmptyRequestWriter,
        fleet_dispatcher: IFleetDispatcher,
        waiting_slot_queue: IWaitingSlotQueue,
        queue_resolver: IQueueResolver,
        notifier: IReturnEmptyEventNotifier,
        uow: IUnitOfWork,
    ):
        self._wash_lookup = wash_lookup
        self._buffer_finder = buffer_finder
        self._cart_mutator = cart_mutator
        self._request_writer = request_writer
        self._fleet_dispatcher = fleet_dispatcher
        self._waiting_slot_queue = waiting_slot_queue
        self._queue_resolver = queue_resolver
        self._notifier = notifier
        self._uow = uow

    def execute(self, request: ReturnEmptyCartRequest) -> ReturnEmptyCartResponse:
        code = RackCode(request.container_code)
        cart = self._wash_lookup.get_wash_cart(code.value)
        loc = self._wash_lookup.get_wash_location(cart.location_id)
        bind_context(container_code=code.value, station_code=loc.location_code)

        buffer_slot = self._buffer_finder.find_next_empty_buffer_slot()
        req_code = f"REQ-{uuid4().hex[:8].upper()}"

        self._cart_mutator.mark_empty(cart.id)
        self._uow.flush()

        if buffer_slot:
            logger.info(
                "call_empty_cart_async candidate decision: selected empty buffer slot %s for cart %s",
                buffer_slot.location_code,
                code.value,
            )
            transport = self._request_writer.create_return_empty(
                request_code=req_code,
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=buffer_slot.id,
                container_id=cart.id,
                status="pending",
                priority=15,
                created_by=request.operator_id,
            )
            bind_context(transport_request_id=transport.id)
            try:
                self._fleet_dispatcher.lock_cart_and_dispatch(
                    transport_request_id=transport.id,
                    cart_id=cart.id,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=buffer_slot.id,
                )
            except Exception:
                self._cart_mutator.set_status(cart.id, "available")
                self._uow.commit()
                raise
        else:
            logger.info(
                "call_empty_cart_async candidate decision: no empty buffer slot for cart %s; queuing",
                code.value,
            )
            transport = self._request_writer.create_return_empty(
                request_code=req_code,
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                status="queued_for_slot",
                priority=15,
                created_by=request.operator_id,
            )
            bind_context(transport_request_id=transport.id)
            self._waiting_slot_queue.enqueue_waiting_slot(
                request_id=transport.id, target_stage_level=0, priority=15
            )

        loc_ids = sorted(
            {
                int(lid)
                for lid in (loc.id, buffer_slot.id if buffer_slot else None)
                if lid is not None
            }
        )
        self._uow.commit()

        if not buffer_slot:
            self._notifier.notify_washing_released_queued(
                location_ids=loc_ids,
                container_code=code.value,
                operator_id=request.operator_id,
            )

        self._queue_resolver.resolve_waiting_slot()

        return ReturnEmptyCartResponse(
            id=transport.id,
            request_code=transport.request_code,
            status=transport.status,
            container_id=transport.container_id,
            destination_location_id=transport.destination_location_id,
        )
