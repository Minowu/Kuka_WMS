"""Port: lock cart + create FleetTask + enqueue fleet submit."""

from abc import ABC, abstractmethod


class IFleetDispatcher(ABC):
    @abstractmethod
    def lock_cart_and_dispatch(
        self,
        transport_request_id: int,
        cart_id: int,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> None:
        raise NotImplementedError
