"""Additional ports for CompleteStage / ReturnEmptyCart orchestration."""

from abc import ABC, abstractmethod
from typing import List, Optional


class IWaitingSlotQueue(ABC):
    @abstractmethod
    def enqueue_waiting_slot(
        self,
        request_id: int,
        target_stage_level: Optional[int],
        priority: int,
    ) -> None:
        raise NotImplementedError


class IStageEventNotifier(ABC):
    @abstractmethod
    def notify_stage_completed(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def notify_stage_queued_wash(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        raise NotImplementedError


class IUnitOfWork(ABC):
    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> None:
        raise NotImplementedError


class IMoveToWashRequestWriter(ABC):
    @abstractmethod
    def create_move_to_wash(
        self,
        *,
        request_code: str,
        item_id: int,
        source_location_id: int,
        destination_location_id: int,
        container_id: int,
        required_stage_level: int,
        status: str,
        priority: int,
        created_by: Optional[int],
    ) -> int:
        raise NotImplementedError
