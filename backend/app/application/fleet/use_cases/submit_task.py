"""Use case: submit pending FleetTask to KUKA Fleet (real path via port)."""

from dataclasses import dataclass
from typing import Any, Optional

from app.application.fleet.ports.fleet_submitter import IFleetSubmitter
from app.application.fleet.ports.fleet_task_repository import IFleetTaskRepository


@dataclass
class SubmitTaskRequest:
    fleet_task_id: Optional[int] = None
    mission_code: Optional[str] = None


@dataclass
class SubmitTaskResponse:
    mission_code: Optional[str]
    status: str
    found: bool
    result: Optional[dict[str, Any]] = None


class SubmitTaskUseCase:
    """
    Real fleet submit use case.
    - If fleet_task_id given → submit via IFleetSubmitter (Celery / worker path).
    - Else lookup by mission_code via repository (status inspection).
    """

    def __init__(
        self,
        fleet_task_repo: IFleetTaskRepository,
        fleet_submitter: Optional[IFleetSubmitter] = None,
    ):
        self._repo = fleet_task_repo
        self._submitter = fleet_submitter

    def execute(self, request: SubmitTaskRequest) -> SubmitTaskResponse:
        if request.fleet_task_id is not None:
            if not self._submitter:
                raise ValueError("Fleet submitter chưa được cấu hình.")
            result = self._submitter.submit_pending_task(request.fleet_task_id)
            status = (result or {}).get("status", "unknown")
            return SubmitTaskResponse(
                mission_code=(result or {}).get("mission_code"),
                status=str(status),
                found=not bool((result or {}).get("skipped")),
                result=result,
            )

        if not request.mission_code:
            raise ValueError("Cần fleet_task_id hoặc mission_code.")

        task = self._repo.get_by_mission_code(request.mission_code)
        if not task:
            return SubmitTaskResponse(
                mission_code=request.mission_code, status="not_found", found=False
            )
        return SubmitTaskResponse(
            mission_code=task.mission_code, status=task.status, found=True
        )
