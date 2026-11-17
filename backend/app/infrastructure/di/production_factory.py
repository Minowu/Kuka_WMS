"""Dependency factories for production / fleet use cases."""

from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.application.fleet.use_cases.handle_webhook import HandleWebhookUseCase
from app.application.production.use_cases.cnc_operations.call_material import CallMaterialUseCase
from app.application.production.use_cases.cnc_operations.complete_stage import CompleteStageUseCase
from app.application.production.use_cases.cnc_operations.return_empty_cart import (
    ReturnEmptyCartUseCase,
)
from app.application.production.use_cases.rack_management.register_rack import RegisterRackUseCase
from app.infrastructure.external_services.production.call_material_adapters import (
    CartSelectorFinder,
    CartSelectorStageResolver,
    EventBusFloorNotifier,
    LockCartFleetDispatcher,
    QueueServiceTransportQueue,
    SqlAlchemyCallMaterialUnitOfWork,
    SqlAlchemyLocationGuard,
)
from app.infrastructure.external_services.production.complete_stage_adapters import (
    CartSelectorMachineStageInfo,
    CartSelectorWashSlotFinder,
    MoveToWashRequestWriter,
    QueueServiceResolver,
    SqlAlchemyActiveCartLookup,
    SqlAlchemyCartStageMutator,
    SqlAlchemyProductionRecorder,
    SqlAlchemyUnitOfWork,
    StageEventNotifier,
    WaitingSlotQueueAdapter,
)
from app.infrastructure.external_services.production.dispatch_ops_adapters import (
    FleetWebhookReceiverAdapter,
)
from app.infrastructure.external_services.production.register_rack_adapters import (
    KukaFleetRackInserter,
    RegisterEventNotifier,
    SqlAlchemyItemCatalog,
    SqlAlchemyRackAtRawMaterialRegistrar,
    SqlAlchemyRawMaterialLocationGuard,
)
from app.infrastructure.external_services.production.return_empty_adapters import (
    CartSelectorEmptyBufferFinder,
    ReturnEmptyEventNotifier,
    SqlAlchemyReturnEmptyRequestWriter,
    SqlAlchemyWashCartLookup,
)
from app.infrastructure.persistence.sqlalchemy.repositories.production import (
    MachineRepositoryImpl,
    RackRepositoryImpl,
    TransportRequestRepositoryImpl,
)
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.production.dispatch.queue_service import QueueService


def _default_dispatch_deps():
    from app.modules.production.dispatch_service import dispatch_service

    return (
        dispatch_service.selector,
        dispatch_service.queue_service,
        dispatch_service._lock_cart_and_dispatch_fleet_task,
        dispatch_service.fleet_client,
        dispatch_service,
    )


def build_call_material_use_case(
    db: Session,
    *,
    selector: Optional[CartSelector] = None,
    queue_service: Optional[QueueService] = None,
    lock_fn: Optional[Callable[..., object]] = None,
) -> CallMaterialUseCase:
    if selector is None or queue_service is None or lock_fn is None:
        selector_d, queue_d, lock_d, _, _ = _default_dispatch_deps()
        selector = selector or selector_d
        queue_service = queue_service or queue_d
        lock_fn = lock_fn or lock_d

    return CallMaterialUseCase(
        location_guard=SqlAlchemyLocationGuard(db, selector),
        stage_resolver=CartSelectorStageResolver(db, selector),
        cart_finder=CartSelectorFinder(db, selector),
        transport_request_repo=TransportRequestRepositoryImpl(db),
        transport_queue=QueueServiceTransportQueue(db, queue_service),
        fleet_dispatcher=LockCartFleetDispatcher(db, lock_fn),
        floor_notifier=EventBusFloorNotifier(db),
        uow=SqlAlchemyCallMaterialUnitOfWork(db),
    )


def get_call_material_use_case(db: Session) -> CallMaterialUseCase:
    return build_call_material_use_case(db)


def build_complete_stage_use_case(
    db: Session,
    *,
    core: Any = None,
    selector: Optional[CartSelector] = None,
    queue_service: Optional[QueueService] = None,
    lock_fn: Optional[Callable[..., object]] = None,
) -> CompleteStageUseCase:
    if core is not None:
        selector = core.selector
        queue_service = core.queue_service
        lock_fn = core.lock_cart_and_dispatch_fleet_task
    elif selector is None or queue_service is None or lock_fn is None:
        selector_d, queue_d, lock_d, _, _ = _default_dispatch_deps()
        selector = selector or selector_d
        queue_service = queue_service or queue_d
        lock_fn = lock_fn or lock_d

    return CompleteStageUseCase(
        cart_lookup=SqlAlchemyActiveCartLookup(db),
        stage_info=CartSelectorMachineStageInfo(db, selector),
        cart_mutator=SqlAlchemyCartStageMutator(db),
        recorder=SqlAlchemyProductionRecorder(db),
        wash_finder=CartSelectorWashSlotFinder(db, selector),
        move_to_wash_writer=MoveToWashRequestWriter(db),
        fleet_dispatcher=LockCartFleetDispatcher(db, lock_fn),
        waiting_slot_queue=WaitingSlotQueueAdapter(db, queue_service),
        queue_resolver=QueueServiceResolver(db, queue_service, lock_fn),
        notifier=StageEventNotifier(db),
        uow=SqlAlchemyUnitOfWork(db),
    )


def get_complete_stage_use_case(db: Session) -> CompleteStageUseCase:
    return build_complete_stage_use_case(db)


def build_register_rack_use_case(
    db: Session,
    *,
    core: Any = None,
    selector: Optional[CartSelector] = None,
    queue_service: Optional[QueueService] = None,
    lock_fn: Optional[Callable[..., object]] = None,
    fleet_client: Optional[KukaFleetClient] = None,
) -> RegisterRackUseCase:
    if core is not None:
        selector = core.selector
        queue_service = core.queue_service
        lock_fn = core.lock_cart_and_dispatch_fleet_task
        fleet_client = getattr(core, "fleet_client", None)
    elif selector is None or queue_service is None or lock_fn is None:
        selector_d, queue_d, lock_d, fleet_d, _ = _default_dispatch_deps()
        selector = selector or selector_d
        queue_service = queue_service or queue_d
        lock_fn = lock_fn or lock_d
        fleet_client = fleet_client or fleet_d

    fleet_client = fleet_client or KukaFleetClient()
    return RegisterRackUseCase(
        location_guard=SqlAlchemyRawMaterialLocationGuard(db),
        item_catalog=SqlAlchemyItemCatalog(db),
        registrar=SqlAlchemyRackAtRawMaterialRegistrar(db),
        fleet_inserter=KukaFleetRackInserter(fleet_client),
        queue_resolver=QueueServiceResolver(db, queue_service, lock_fn),
        notifier=RegisterEventNotifier(db),
        uow=SqlAlchemyUnitOfWork(db),
    )


def get_register_rack_use_case(db: Session) -> RegisterRackUseCase:
    return build_register_rack_use_case(db)


def build_return_empty_cart_use_case(
    db: Session,
    *,
    core: Any = None,
    selector: Optional[CartSelector] = None,
    queue_service: Optional[QueueService] = None,
    lock_fn: Optional[Callable[..., object]] = None,
) -> ReturnEmptyCartUseCase:
    if core is not None:
        selector = core.selector
        queue_service = core.queue_service
        lock_fn = core.lock_cart_and_dispatch_fleet_task
    elif selector is None or queue_service is None or lock_fn is None:
        selector_d, queue_d, lock_d, _, _ = _default_dispatch_deps()
        selector = selector or selector_d
        queue_service = queue_service or queue_d
        lock_fn = lock_fn or lock_d

    return ReturnEmptyCartUseCase(
        wash_lookup=SqlAlchemyWashCartLookup(db),
        buffer_finder=CartSelectorEmptyBufferFinder(db, selector),
        cart_mutator=SqlAlchemyCartStageMutator(db),
        request_writer=SqlAlchemyReturnEmptyRequestWriter(db),
        fleet_dispatcher=LockCartFleetDispatcher(db, lock_fn),
        waiting_slot_queue=WaitingSlotQueueAdapter(db, queue_service),
        queue_resolver=QueueServiceResolver(db, queue_service, lock_fn),
        notifier=ReturnEmptyEventNotifier(db),
        uow=SqlAlchemyUnitOfWork(db),
    )


def get_return_empty_cart_use_case(db: Session) -> ReturnEmptyCartUseCase:
    return build_return_empty_cart_use_case(db)


def build_handle_webhook_use_case(db: Session) -> HandleWebhookUseCase:
    _, _, _, _, dispatch_service = _default_dispatch_deps()
    return HandleWebhookUseCase(
        receiver=FleetWebhookReceiverAdapter(db, dispatch_service.receive_task_status)
    )


def get_handle_webhook_use_case(db: Session) -> HandleWebhookUseCase:
    return build_handle_webhook_use_case(db)


def get_machine_repository(db: Session) -> MachineRepositoryImpl:
    return MachineRepositoryImpl(db)


def get_rack_repository(db: Session) -> RackRepositoryImpl:
    return RackRepositoryImpl(db)


def get_transport_request_repository(db: Session) -> TransportRequestRepositoryImpl:
    return TransportRequestRepositoryImpl(db)
