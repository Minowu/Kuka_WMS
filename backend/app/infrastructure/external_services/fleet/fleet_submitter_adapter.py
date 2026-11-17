"""Adapter: IFleetSubmitter → run_submit_pending_fleet_task."""

from typing import Any, Optional

from app.application.fleet.ports.fleet_submitter import IFleetSubmitter
from app.infrastructure.external_services.fleet.submit_pending_impl import (
    run_submit_pending_fleet_task,
)


class FleetSubmitterAdapter(IFleetSubmitter):
    def submit_pending_task(self, fleet_task_id: int) -> Optional[dict[str, Any]]:
        return run_submit_pending_fleet_task(fleet_task_id)
