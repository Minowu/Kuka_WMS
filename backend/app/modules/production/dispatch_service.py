"""
Production & AMR Dispatch Engine Service.

Implements:
1. User Location Assignment (`assign_locations_to_user` — unrestricted assignment across zones/machines).
2. Raw Material Rack QR Registration (reusable physical rack `container_code` -> Fleet POST insert + ItemStock upsert + auto-resolve WAITING_CART queue).
3. Cart Selection (FIFO for Level 0 raw material; 2D Euclidean distance + FIFO with `FOR UPDATE SKIP LOCKED` for Level > 0).
4. POS1 / POS2 CNC Slot Allocation (normalized 3NF via `Machine` & `RouteStepMachine`) & Waiting Queue Management (`TransportQueue`).
5. Stage Progression (`complete_machining_stage`: Intermediate steps update stage_level & trigger WAITING_CART scan; Final CNC step pushes to Washing -> Empty Cart Return).
6. Empty Cart Buffer (`EMPTY_CART_BUFFER`): Round-Robin distribution across slots 1..4 & automatic `fleet_remove_rack` + ItemStock deactivation upon AMR dropoff.
7. KUKA Fleet Manager (RCS/ICS) HTTP Adapter (`add_task`, `create_fleet_task`, and 6 Fleet command hooks) & Webhook Callback (`receive_task_status` -> `TaskStatus` + `FleetTask` + `ItemStock` settlement).
"""

from datetime import datetime, timezone
import json
import math
from typing import Any, Optional
import uuid

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logger import get_logger
from app.modules.production.production_models import (
    FLEET_MISSION_STATUS,
    MAPPING_STATUS,
    FleetApiCall,
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TaskStatus,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")


def _ics_configured() -> bool:
    base = (settings.ics_base_url or "").strip()
    return bool(base and base != "Your RCS Server path" and base.startswith("http"))


class IcsError(Exception):
    """Exception raised when communicating with KUKA Fleet Manager (ICS/RCS)."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class DispatchService:
    """Core service for CNC work-in-progress (WIP) cart routing and KUKA AMR fleet dispatch."""

    # =========================================================================
    # 0. KUKA FLEET MANAGER HTTP ADAPTER & COMMAND HOOKS (100% REAL KUKA FLEET)
    # =========================================================================

    def _post_kuka(
        self,
        endpoint_path: str,
        payload: dict[str, Any],
        api_name: str,
        mission_code: Optional[str] = None,
        container_code: Optional[str] = None,
        request_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """Low-level HTTP POST to KUKA Fleet Manager with audit logging in fleet_api_call."""
        req_id = request_id or str(payload.get("requestId") or f"REQ_{uuid.uuid4().hex[:12].upper()}")
        base = getattr(settings, "kuka_base_url", None) or getattr(settings, "ics_base_url", "")
        base = base.rstrip("/")
        endpoint = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        url = f"{base}{endpoint}"

        if not _ics_configured():
            error_msg = f"KUKA Fleet API chưa được cấu hình hoặc offline — không thể điều xe {api_name}"
            logger.error(error_msg)
            err_resp = {"code": -1, "message": error_msg, "success": False}
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=503,
                    response_body=err_resp,
                    error=error_msg,
                    success=False,
                )
                db.add(call_log)
                db.flush()
            return err_resp

        timeout_sec = float(getattr(settings, "kuka_http_timeout_seconds", 5.0))
        http_status = None
        resp_data = None
        error_msg = None
        headers = {
            "Content-Type": "application/json",
            "orgId": getattr(settings, "kuka_org_id", "KUKA011021"),
        }
        token = getattr(settings, "kuka_access_token", None) or getattr(settings, "kuka_api_token", None)
        if token:
            headers["Authorization"] = token

        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_sec)) as client:
                response = client.post(url, json=payload, headers=headers)
                http_status = response.status_code
                response.raise_for_status()
                resp_data = response.json()
            logger.info("KUKA Fleet POST %s [%s] response: %s", endpoint_path, api_name, resp_data)
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=http_status,
                    response_body=resp_data,
                    success=True,
                )
                db.add(call_log)
                db.flush()
            return resp_data
        except httpx.HTTPStatusError as e:
            http_status = e.response.status_code
            error_msg = f"KUKA Fleet server error ({http_status}): {e.response.text}"
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=http_status,
                    response_body=None,
                    success=False,
                    error=error_msg,
                )
                db.add(call_log)
                db.flush()
            raise IcsError(error_msg, retryable=(http_status >= 500)) from e
        except httpx.RequestError as e:
            error_msg = f"Cannot reach KUKA Fleet server: {e}"
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=None,
                    response_body=None,
                    success=False,
                    error=error_msg,
                )
                db.add(call_log)
                db.flush()
            raise IcsError(error_msg, retryable=True) from e

    def add_task(self, payload: dict[str, Any], endpoint_path: str = "/amr/submitMission") -> dict[str, Any]:
        """Backward-compatibility bridge for raw task dispatching."""
        return self._post_kuka(endpoint_path, payload, api_name="raw_submitMission")

    def fleet_container_in(
        self,
        location_code: str,
        container_code: str,
        is_new: bool = False,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/containerIn]
        Register presence of physical container (`container_code`) at location (`location_code`).
        """
        request_id = f"CIN{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "containerCode": container_code,
            "enterOrientation": "",
            "isNew": is_new,
            "position": location_code,
            "requestId": request_id,
        }
        logger.info("Fleet containerIn: container=%s at position=%s isNew=%s", container_code, location_code, is_new)
        return self._post_kuka(
            "/amr/containerIn",
            payload,
            api_name="containerIn",
            container_code=container_code,
            request_id=request_id,
            db=db,
        )

    def fleet_insert_rack(self, location_code: str, container_code: str) -> dict[str, Any]:
        """Alias for fleet_container_in."""
        return self.fleet_container_in(location_code, container_code)

    def fleet_container_out(
        self,
        location_code: str = "",
        container_code: str = "",
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/containerOut]
        De-register physical container (`container_code`) when returned to Empty Cart Buffer.
        """
        request_id = f"COUT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "requestId": request_id,
            "containerType": "",
            "containerCode": container_code,
            "position": location_code,
            "isDelete": False,
        }
        logger.info("Fleet containerOut: container=%s at position=%s", container_code, location_code)
        return self._post_kuka(
            "/amr/containerOut",
            payload,
            api_name="containerOut",
            container_code=container_code,
            request_id=request_id,
            db=db,
        )

    def fleet_remove_rack(self, location_code: str, container_code: str) -> dict[str, Any]:
        """Alias for fleet_container_out."""
        return self.fleet_container_out(location_code=location_code, container_code=container_code)

    def fleet_cancel_task(self, mission_code: str) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/missionCancel]
        Cancel an active Fleet task by `missionCode`.
        """
        request_id = f"CXL{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "requestId": request_id,
            "missionCode": mission_code,
            "containerCode": "",
            "position": "",
            "cancelMode": "FORCE",
        }
        return self._post_kuka(
            "/amr/missionCancel",
            payload,
            api_name="missionCancel",
            mission_code=mission_code,
            request_id=request_id,
        )

    # -------------------------------------------------------------------------
    # 3 Move Functions (User constraint D15: keep 3 distinct explicit functions)
    # -------------------------------------------------------------------------

    def fleet_move_material(
        self,
        task: FleetTask,
        pickup_code: str,
        dropoff_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 1 - Raw Material -> CNC or CNC Level N -> CNC Level N+1]
        Dispatches AMR via POST /amr/submitMission with 2 waypoints (Sequence 1 pickup, Sequence 2 dropoff).
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": dropoff_code,
                "type": "NODE_POINT",
                "putDown": True,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": False,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:material",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_to_wash(
        self,
        task: FleetTask,
        pickup_code: str,
        wash_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 2 - Final CNC -> Washing Station]
        Dispatches AMR via POST /amr/submitMission with 2 waypoints.
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": wash_code,
                "type": "NODE_POINT",
                "putDown": True,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": False,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:wash",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_empty_container(
        self,
        task: FleetTask,
        pickup_code: str,
        buffer_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 3 - Empty Container Return -> Empty Cart Buffer]
        Dispatches AMR via POST /amr/submitMission with 2 waypoints.
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": buffer_code,
                "type": "NODE_POINT",
                "putDown": True,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": False,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:empty_container",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_empty_rack(self, task: FleetTask, pickup_code: str, buffer_code: str, container_code: Optional[str]) -> dict[str, Any]:
        """Alias for fleet_move_empty_container."""
        return self.fleet_move_empty_container(task, pickup_code, buffer_code, container_code)

    def submit_fleet_task(self, db: Session, task: FleetTask, request_type: str = "CALL_MATERIAL") -> FleetTask:
        """Submit an already-persisted FleetTask to KUKA Fleet Manager via submitMission."""
        pickup_loc = db.query(Location).filter(Location.id == task.pickup_location_id).first()
        dropoff_loc = db.query(Location).filter(Location.id == task.dropoff_location_id).first()
        container = db.query(ItemStock).filter(ItemStock.id == task.container_id).first() if task.container_id else None

        pickup_code = pickup_loc.location_code if pickup_loc else str(task.pickup_location_id)
        dropoff_code = dropoff_loc.location_code if dropoff_loc else str(task.dropoff_location_id)
        c_code = container.container_code if container else task.container_code

        try:
            if request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
                self.fleet_move_to_wash(task, pickup_code, dropoff_code, c_code, db=db)
            elif request_type == "RETURN_EMPTY_CART":
                self.fleet_move_empty_container(task, pickup_code, dropoff_code, c_code, db=db)
            else:
                self.fleet_move_material(task, pickup_code, dropoff_code, c_code, db=db)

            task.status = "sent"
            task.sent_at = datetime.now(timezone.utc)
            db.flush()
        except IcsError as e:
            logger.warning("Could not submit task %s to Fleet immediately: %s", task.mission_code, e)
            task.status = "pending_submit"
            task.submit_attempts += 1
            task.error_message = str(e)
            db.flush()
        return task

    def create_fleet_task(self, db: Session, task: FleetTask, request_type: str = "CALL_MATERIAL") -> FleetTask:
        """Alias for submit_fleet_task."""
        return self.submit_fleet_task(db, task, request_type=request_type)

    # =========================================================================
    # 1. USER LOCATION ASSIGNMENT (UNRESTRICTED)
    # =========================================================================

    def assign_locations_to_user(
        self,
        db: Session,
        user_id: int,
        location_ids: list[int],
    ) -> list[UserLocation]:
        """
        Assign stations/locations to an operator.
        Strictly enforces 1 user = 1 area:
        - Automatically revokes all existing assigned locations for this user.
        - Validates that all newly selected locations belong to the same functional area
          (e.g., RAW_MATERIAL, CNC_SLOT, or WASHING_SLOT).
        """
        unique_loc_ids = list(dict.fromkeys(location_ids))

        if unique_loc_ids:
            loc_objs = (
                db.query(Location)
                .filter(Location.id.in_(unique_loc_ids), Location.is_active.is_(True))
                .all()
            )
            if len(loc_objs) != len(unique_loc_ids):
                raise ValueError("Một hoặc nhiều vị trí (Location) không tồn tại hoặc đã bị khóa.")

            # Enforce 1 user = 1 area
            area_types = {loc.location_type for loc in loc_objs}
            if len(area_types) > 1:
                raise ValueError("Một tài khoản công nhân chỉ có thể được phân quyền trong 1 khu vực duy nhất.")

        # Revoke all existing locations for this user across any previous area
        db.query(UserLocation).filter(UserLocation.user_id == user_id).delete(synchronize_session=False)

        records = [
            UserLocation(user_id=user_id, location_id=loc_id)
            for loc_id in unique_loc_ids
        ]
        db.add_all(records)
        db.commit()
        return records

    # =========================================================================
    # 2. RAW MATERIAL RACK QR REGISTRATION (REUSABLE RACK QR -> FLEET INSERT + AUTO DISPATCH)
    # =========================================================================

    def register_rack_at_raw_material(
        self,
        db: Session,
        location_id: int,
        item_id: int,
        container_code: str,
        quantity: Optional[int] = None,
        lot_number: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        When a worker at the Raw Material zone:
        1. Selects a Raw Material location (`location_id`)
        2. Selects a Product Model (`item_id`)
        3. Scans the reusable physical Rack QR (`container_code`)

        This method:
        - Validates that the location is free.
        - Sends `fleet_insert_rack` POST to KUKA Fleet Manager so Fleet binds the rack at that node.
        - Creates or reuses the `ItemStock` row for `container_code` with `current_stage_level = 0`, `is_locked = False`.
        - Immediately calls `try_resolve_waiting_cart_queue(db, stage_level=0)` so if a CNC machine is
          already waiting in `TransportQueue` (`WAITING_CART`) for that model, an AMR is dispatched right away!
        """
        clean_container_code = container_code.strip()
        if not clean_container_code:
            raise ValueError("Mã QR của rack (container_code) không được để trống.")

        location = (
            db.query(Location)
            .filter(Location.id == location_id, Location.is_active.is_(True))
            .first()
        )
        if not location:
            raise ValueError(f"Vị trí ID={location_id} không tồn tại hoặc đã ngừng hoạt động.")

        item = (
            db.query(Item)
            .filter(Item.id == item_id)
            .first()
        )
        if not item:
            raise ValueError(f"Model sản phẩm ID={item_id} không tồn tại hoặc đã ngừng hoạt động.")

        # Check if another active cart is already occupying this location
        occupying_cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == location.id,
                ItemStock.is_active.is_(True),
                ItemStock.container_code != clean_container_code,
            )
            .first()
        )
        if occupying_cart:
            raise ValueError(
                f"Vị trí '{location.location_code}' đang có xe/rack '{occupying_cart.container_code}' đỗ."
            )

        qty = quantity if (quantity is not None and quantity > 0) else (item.standard_quantity_per_cart or 120)

        # 1. Notify KUKA Fleet Manager to insert/bind the rack at this location
        self.fleet_insert_rack(location.location_code, clean_container_code)

        # 2. Reuse existing ItemStock row if rack QR was used in a previous cycle, or create new
        cart = db.query(ItemStock).filter(ItemStock.container_code == clean_container_code).first()
        now = datetime.now(timezone.utc)
        if cart:
            if cart.is_locked:
                raise ValueError(
                    f"Rack '{clean_container_code}' đang bị khóa bởi tác vụ vận chuyển '{cart.locked_by_mission_code}'."
                )
            cart.item_id = item.id
            cart.location_id = location.id
            cart.destination_location_id = None
            cart.quantity = qty
            cart.current_stage_level = 0
            cart.status = "available"
            cart.is_active = True
            cart.is_locked = False
            cart.locked_by_mission_code = None
            cart.fleet_registered = True
            cart.created_at = now
        else:
            cart = ItemStock(
                container_code=clean_container_code,
                item_id=item.id,
                location_id=location.id,
                destination_location_id=None,
                quantity=qty,
                current_stage_level=0,
                status="available",
                is_active=True,
                is_locked=False,
                locked_by_mission_code=None,
                fleet_registered=True,
            )
            db.add(cart)

        db.commit()
        db.refresh(cart)

        # 3. Check if any CNC station is waiting in TransportQueue (WAITING_CART) for Level 0
        resolved_count = self.try_resolve_waiting_cart_queue(db, stage_level=0)
        db.refresh(cart)

        return {
            "container_id": cart.id,
            "container_code": cart.container_code,
            "item_id": item.id,
            "sku": item.sku,
            "location_id": location.id,
            "location_code": location.location_code,
            "quantity": int(cart.quantity),
            "current_stage_level": cart.current_stage_level,
            "is_locked": cart.is_locked,
            "fleet_inserted": True,
            "resolved_queue_count": resolved_count,
            "dispatched_mission_code": cart.locked_by_mission_code,
        }

    # =========================================================================
    # 3. STAGE LEVEL RESOLUTION, CART SELECTION & SLOT ALLOCATION HELPERS
    # =========================================================================

    @staticmethod
    def calculate_distance(loc1: Optional[Location], loc2: Optional[Location]) -> float:
        """Calculate 2D Euclidean distance between two locations on the factory map."""
        if not loc1 or not loc2:
            return float("inf")
        if loc1.map_x is None or loc1.map_y is None or loc2.map_x is None or loc2.map_y is None:
            return float("inf")
        dx = float(loc1.map_x) - float(loc2.map_x)
        dy = float(loc1.map_y) - float(loc2.map_y)
        return math.sqrt(dx * dx + dy * dy)

    def get_stage_info_for_machine(
        self,
        db: Session,
        location: Location,
        item_id: int,
    ) -> tuple[int, int, bool]:
        """
        Resolve `(input_required_level, target_stage_level, is_final_cnc_step)` for a CNC `location`
        machining `item_id` using the normalized 3NF `ProductionRoute` -> `RouteStep` -> `RouteStepMachine`.
        """
        route = (
            db.query(ProductionRoute)
            .filter(
                ProductionRoute.item_id == item_id,
                ProductionRoute.is_active.is_(True),
            )
            .first()
        )
        steps: list[RouteStep] = []
        if route:
            steps = (
                db.query(RouteStep)
                .options(joinedload(RouteStep.allowed_machine_links).joinedload(RouteStepMachine.machine))
                .filter(RouteStep.route_id == route.id)
                .order_by(RouteStep.stage_level.asc(), RouteStep.step_number.asc())
                .all()
            )

        machine_id = location.machine_id
        machine_code = location.machine_code

        # 1. Match via normalized 3NF RouteStepMachine links
        if steps and (machine_id or machine_code):
            for idx, step in enumerate(steps):
                matched = False
                for link in step.allowed_machine_links or []:
                    if machine_id and link.machine_id == machine_id:
                        matched = True
                        break
                    if machine_code and link.machine and link.machine.machine_code == machine_code:
                        matched = True
                        break
                if matched:
                    input_lvl = max(step.stage_level - 1, 0)
                    is_final = bool(step.is_final_cnc_step) or (idx == len(steps) - 1)
                    return (input_lvl, step.stage_level, is_final)

        # 2. Fallback by machine_code naming or first step
        if machine_code == "CNC-03":
            return (1, 2, False)
        if machine_code == "CNC-04":
            return (2, 3, True)
        if steps:
            first_step = steps[0]
            is_final = bool(first_step.is_final_cnc_step) or len(steps) == 1
            return (max(first_step.stage_level - 1, 0), first_step.stage_level, is_final)
        return (0, 1, False)

    def find_fifo_available_cart(
        self,
        db: Session,
        item_id: int,
        stage_level: int = 0,
        target_location: Optional[Location] = None,
    ) -> Optional[ItemStock]:
        """
        Select an available cart matching `item_id` and `current_stage_level`:
        - For `stage_level == 0` (Raw Material): FIFO order (`created_at ASC, id ASC`).
        - For `stage_level > 0` (CNC WIP transfer): Nearest 2D Euclidean distance to `target_location`
          (if map coordinates exist), tie-broken by FIFO (`created_at ASC, id ASC`).
        Uses `with_for_update(of=ItemStock, skip_locked=True)` so concurrent requests never pick the same cart.
        """
        location_types = ["RAW_MATERIAL"] if stage_level == 0 else ["CNC_SLOT", "RAW_MATERIAL"]

        candidates = (
            db.query(ItemStock)
            .join(Location, ItemStock.location_id == Location.id)
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.current_stage_level == stage_level,
                ItemStock.is_locked.is_(False),
                ItemStock.is_active.is_(True),
                ItemStock.quantity > 0,
                Location.location_type.in_(location_types),
                Location.is_active.is_(True),
            )
            .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
            .with_for_update(of=ItemStock, skip_locked=True)
            .all()
        )
        if not candidates:
            return None

        if (
            stage_level > 0
            and target_location is not None
            and target_location.map_x is not None
            and target_location.map_y is not None
        ):
            candidates_with_coords = [
                c for c in candidates if c.location and c.location.map_x is not None and c.location.map_y is not None
            ]
            if candidates_with_coords:
                candidates.sort(
                    key=lambda c: (
                        self.calculate_distance(c.location, target_location),
                        c.created_at or datetime.min.replace(tzinfo=timezone.utc),
                        c.id,
                    )
                )

        return candidates[0]

    def _is_location_free(self, db: Session, location_id: int) -> bool:
        """
        A location is free if:
        1. No active cart is currently sitting at `location_id`.
        2. No locked cart is currently in-transit heading to `destination_location_id == location_id`.
        3. No active FleetTask has `dropoff_location_id == location_id`.
        """
        occupied_by_cart = (
            db.query(ItemStock.id)
            .filter(
                ItemStock.location_id == location_id,
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if occupied_by_cart:
            return False

        reserved_by_cart = (
            db.query(ItemStock.id)
            .filter(
                ItemStock.destination_location_id == location_id,
                ItemStock.is_locked.is_(True),
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if reserved_by_cart:
            return False

        reserved_by_task = (
            db.query(FleetTask.id)
            .filter(
                FleetTask.dropoff_location_id == location_id,
                FleetTask.status.in_(["created", "sent", "in_progress"]),
            )
            .first()
        )
        if reserved_by_task:
            return False

        return True

    def find_available_slot_to_wash(
        self,
        db: Session,
    ) -> Optional[Location]:
        """
        Tìm ô đỗ còn trống tại Khu Tẩy Rửa (`location_type == 'WASHING_SLOT'`: WASH-01..04).
        Dùng khi máy CNC công đoạn cuối hoàn thành gia công để chuyển xe phôi sang rửa.
        """
        candidate_slots = (
            db.query(Location)
            .filter(
                Location.location_type == "WASHING_SLOT",
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc().nullsfirst(), Location.id.asc())
            .all()
        )
        for slot in candidate_slots:
            if self._is_location_free(db, slot.id):
                return slot
        return None

    def find_next_empty_buffer_slot(self, db: Session) -> Optional[Location]:
        """
        Distribute empty carts sequentially (Round-Robin: 1 -> 2 -> 3 -> 4 -> 1) across
        `EMPTY_CART_BUFFER` locations so AMRs do not pile all empty carts onto slot 1.
        """
        buffer_slots = (
            db.query(Location)
            .filter(
                Location.location_type == "EMPTY_CART_BUFFER",
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc().nullsfirst(), Location.id.asc())
            .all()
        )
        if not buffer_slots:
            return None

        buffer_ids = [slot.id for slot in buffer_slots]
        last_task = (
            db.query(FleetTask)
            .filter(FleetTask.dropoff_location_id.in_(buffer_ids))
            .order_by(FleetTask.id.desc())
            .first()
        )

        if last_task and last_task.dropoff_location_id in buffer_ids:
            last_idx = buffer_ids.index(last_task.dropoff_location_id)
            ordered_slots = buffer_slots[last_idx + 1 :] + buffer_slots[: last_idx + 1]
        else:
            ordered_slots = buffer_slots

        for slot in ordered_slots:
            if self._is_location_free(db, slot.id):
                return slot
        return None

    # =========================================================================
    # 4. CALL MATERIAL TO CNC STATION (PULL + POS1/POS2 BUFFERING + QUEUEING)
    # =========================================================================

    def call_material_to_cnc(
        self,
        db: Session,
        destination_location_id: int,
        item_id: Optional[int] = None,
        required_stage_level: Optional[int] = None,
        created_by: Optional[int] = None,
        priority: int = 10,
    ) -> TransportRequest:
        """
        Công nhân tại máy CNC bấm gọi phôi (1-Chạm).
        - Tự động tra cứu Model và Stage Level từ RouteStepMachine trong ProductionRoute của máy CNC.
        - Kiểm tra an toàn vị trí (_is_location_free).
        - Tìm khay phôi thỏa mãn (FIFO cho Level 0, Euclidean Distance cho Level > 0).
        - Nếu có phôi: Khóa khay và điều AMR (FleetTask).
        - Nếu hết phôi: Đưa vào hàng đợi TransportQueue (WAITING_CART).
        """
        dest_loc = (
            db.query(Location)
            .filter(Location.id == destination_location_id, Location.is_active.is_(True))
            .first()
        )
        if not dest_loc:
            raise ValueError("Vị trí đích (Location) không tồn tại hoặc đã bị khóa.")

        # Check if target slot chosen by operator is free
        if not self._is_location_free(db, dest_loc.id):
            raise ValueError(
                f"Vị trí '{dest_loc.location_code}' hiện đang có xe hoặc đã có AMR đặt chỗ. Vui lòng chọn vị trí trống."
            )

        if item_id is None:
            m_id = dest_loc.machine_id
            m_code = dest_loc.machine_code
            step_link = None
            if m_id:
                step_link = (
                    db.query(RouteStepMachine)
                    .join(RouteStep, RouteStepMachine.route_step_id == RouteStep.id)
                    .join(ProductionRoute, RouteStep.route_id == ProductionRoute.id)
                    .filter(
                        RouteStepMachine.machine_id == m_id,
                        ProductionRoute.is_active.is_(True),
                    )
                    .first()
                )
            if not step_link and m_code:
                step_link = (
                    db.query(RouteStepMachine)
                    .join(Machine, RouteStepMachine.machine_id == Machine.id)
                    .join(RouteStep, RouteStepMachine.route_step_id == RouteStep.id)
                    .join(ProductionRoute, RouteStep.route_id == ProductionRoute.id)
                    .filter(
                        Machine.machine_code == m_code,
                        ProductionRoute.is_active.is_(True),
                    )
                    .first()
                )
            if step_link and step_link.route_step and step_link.route_step.route:
                item_id = step_link.route_step.route.item_id
            else:
                first_item = db.query(Item).filter(Item.is_active.is_(True)).first()
                if first_item:
                    item_id = first_item.id
                else:
                    raise ValueError(
                        f"Không thể xác định Model sản phẩm cho vị trí '{dest_loc.location_code}'. Vui lòng cấu hình Route cho máy."
                    )

        if required_stage_level is None:
            input_lvl, _, _ = self.get_stage_info_for_machine(db, dest_loc, item_id)
            required_stage_level = input_lvl

        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="CALL_MATERIAL",
            item_id=item_id,
            destination_location_id=dest_loc.id,
            required_stage_level=required_stage_level,
            status="pending",
            priority=priority,
            created_by=created_by,
        )
        db.add(transport_req)
        db.flush()

        # Find available cart (FIFO for Level 0, Euclidean distance + FIFO for Level > 0)
        cart = self.find_fifo_available_cart(
            db,
            item_id=item_id,
            stage_level=required_stage_level,
            target_location=dest_loc,
        )
        if cart:
            self._lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=dest_loc.id,
            )
        else:
            transport_req.status = "queued_for_cart"
            queue_entry = TransportQueue(
                request_id=transport_req.id,
                queue_type="WAITING_CART",
                target_stage_level=required_stage_level,
                status="PENDING",
                priority=priority,
            )
            db.add(queue_entry)

        db.commit()
        db.refresh(transport_req)
        return transport_req

    # =========================================================================
    # 5. COMPLETE MACHINING STAGE (INTERMEDIATE PULL/SCAN vs FINAL AUTO-WASH)
    # =========================================================================

    def complete_machining_stage(
        self,
        db: Session,
        container_code: Optional[str] = None,
        location_id: Optional[int] = None,
        operator_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Called when an operator finishes machining a cart at a CNC station:
        1. Increments `cart.current_stage_level` (e.g., 0 -> 1, 1 -> 2, 2 -> 3).
        2. Records a `ProductionRecord` audit entry.
        3. Evaluates the active `ProductionRoute` for `cart.item_id`:
           - Intermediate CNC Step (`is_final_cnc_step=False` and next `RouteStep` exists):
             * Keeps the cart unlocked at its current station (`status='available'`, `current_stage_level=completed_stage`).
             * Immediately scans `TransportQueue` (`WAITING_CART`) for `stage_level == completed_stage`:
               if a downstream CNC station has already called for this Model, dispatches AMR right away!
               Otherwise, the cart waits at its current station until a downstream CNC station calls it.
           - Final CNC Step (`is_final_cnc_step=True` or no next `RouteStep`):
             * Automatically routes the cart to an available `WASHING_SLOT` (`MOVE_TO_WASH`),
               or enqueues into `TransportQueue` (`WAITING_SLOT`) if all 4 washing slots are full.
        """
        query = db.query(ItemStock).filter(ItemStock.is_active.is_(True))
        if container_code and container_code.strip():
            query = query.filter(ItemStock.container_code == container_code.strip())
        elif location_id:
            query = query.filter(ItemStock.location_id == location_id)
        else:
            raise ValueError("Phải cung cấp mã xe (container_code) hoặc vị trí trạm máy (location_id).")

        cart = query.with_for_update(of=ItemStock).first()
        if not cart:
            raise ValueError(f"Không tìm thấy xe hàng hợp lệ (container_code='{container_code}', location_id={location_id}).")
        if cart.is_locked:
            raise ValueError(f"Xe hàng '{cart.container_code}' đang bị khóa bởi tác vụ vận chuyển khác.")
        if not cart.location_id:
            raise ValueError(f"Xe hàng '{cart.container_code}' chưa có vị trí hiện tại.")

        current_loc = db.query(Location).filter(Location.id == cart.location_id).first()

        # Advance stage level: if cart arrived as raw material (0), finishing the first CNC machine brings it to 1
        completed_stage = (cart.current_stage_level or 0) + 1
        cart.current_stage_level = completed_stage
        cart.status = "available"
        cart.is_locked = False
        cart.locked_by_mission_code = None
        cart.destination_location_id = None

        prod_record = ProductionRecord(
            container_code=cart.container_code,
            container_id=cart.id,
            item_id=cart.item_id,
            machine_code=current_loc.machine_code if current_loc else None,
            location_id=cart.location_id,
            stage_level=completed_stage,
            operator_id=operator_id,
            notes=notes,
        )
        db.add(prod_record)
        db.flush()

        # Lookup active production route for this item
        route = (
            db.query(ProductionRoute)
            .filter(
                ProductionRoute.item_id == cart.item_id,
                ProductionRoute.is_active.is_(True),
            )
            .first()
        )

        next_stage_level = completed_stage + 1
        next_step: Optional[RouteStep] = None
        current_step: Optional[RouteStep] = None

        if route:
            current_step = (
                db.query(RouteStep)
                .filter(
                    RouteStep.route_id == route.id,
                    RouteStep.stage_level == completed_stage,
                )
                .first()
            )
            if not (current_step and current_step.is_final_cnc_step):
                next_step = (
                    db.query(RouteStep)
                    .options(
                        joinedload(RouteStep.allowed_machine_links).joinedload(RouteStepMachine.machine)
                    )
                    .filter(
                        RouteStep.route_id == route.id,
                        RouteStep.stage_level == next_stage_level,
                    )
                    .first()
                )

        is_final_cnc_step = bool((current_step and current_step.is_final_cnc_step) or (next_step is None))

        if not is_final_cnc_step:
            # INTERMEDIATE STEP (PULL + ALWAYS SCAN):
            # Persist the updated stage level and immediately scan WAITING_CART queue
            # in case a downstream CNC station has already requested this cart level!
            db.commit()
            resolved_count = self.try_resolve_waiting_cart_queue(db, stage_level=completed_stage)
            db.refresh(cart)

            matched_req_code: Optional[str] = None
            if cart.is_locked and cart.locked_by_mission_code:
                ft = db.query(FleetTask).filter(FleetTask.mission_code == cart.locked_by_mission_code).first()
                if ft and ft.request:
                    matched_req_code = ft.request.request_code

            action_result = (
                "DISPATCHED_TO_WAITING_CNC" if (resolved_count > 0 and cart.is_locked) else "STAGE_COMPLETED_WAITING_CALL"
            )
            return {
                "container_code": cart.container_code,
                "completed_stage_level": completed_stage,
                "is_final_cnc_step": False,
                "action": action_result,
                "resolved_queue_count": resolved_count,
                "dispatched_mission_code": cart.locked_by_mission_code,
                "request_code": matched_req_code,
            }

        # FINAL CNC STEP -> Automatically push to WASHING_SLOT
        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        wash_slot = self.find_available_slot_to_wash(db)
        if wash_slot:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="MOVE_TO_WASH",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=wash_slot.id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="pending",
                priority=5,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            self._lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=wash_slot.id,
            )
            action_result = "DISPATCHED_TO_WASHING"
        else:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="MOVE_TO_WASH",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="queued_for_slot",
                priority=5,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            queue_entry = TransportQueue(
                request_id=transport_req.id,
                queue_type="WAITING_SLOT",
                target_stage_level=99,  # 99 denotes WASHING_SLOT
                status="PENDING",
                priority=5,
            )
            db.add(queue_entry)
            action_result = "QUEUED_FOR_WASHING_SLOT"

        db.commit()
        return {
            "container_code": cart.container_code,
            "completed_stage_level": completed_stage,
            "is_final_cnc_step": True,
            "action": action_result,
            "request_code": transport_req.request_code,
        }

    # =========================================================================
    # 6. RETURN EMPTY CART FROM WASHING (SCENARIO 4)
    # =========================================================================

    def complete_washing_and_return_empty_cart(
        self,
        db: Session,
        container_code: str,
        operator_id: Optional[int] = None,
    ) -> TransportRequest:
        """
        Scenario 4 (Hoàn thành Tẩy rửa -> Trả xe rỗng về Bãi đệm EMPTY_CART_BUFFER):
        Khi công nhân tại Khu Tẩy Rửa nhấc chi tiết đưa vào bể rửa, xe phôi trở thành xe rỗng.
        Hệ thống đặt quantity = 0, status = 'empty', current_stage_level = 0.
        Tìm ô bãi đệm xe rỗng theo cơ chế xoay vòng Round-Robin (EMPTY-01..04) và điều AMR chở xe về.
        (Lưu ý: Máy CNC không bao giờ trả xe rỗng; chỉ có sau công đoạn Tẩy Rửa mới phát sinh xe rỗng).
        """
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.container_code == container_code.strip(), ItemStock.is_active.is_(True))
            .with_for_update(of=ItemStock)
            .first()
        )
        if not cart or not cart.location_id:
            raise ValueError(f"Không tìm thấy container '{container_code}' tại vị trí hợp lệ.")
        if cart.is_locked:
            raise ValueError(f"Xe '{container_code}' đang bị khóa bởi lệnh vận chuyển khác.")

        cart.quantity = 0
        cart.current_stage_level = 0
        cart.status = "empty"

        empty_buffer = self.find_next_empty_buffer_slot(db)
        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        if empty_buffer:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=empty_buffer.id,
                container_id=cart.id,
                required_stage_level=0,
                status="pending",
                priority=15,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            self._lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=empty_buffer.id,
            )
        else:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                required_stage_level=0,
                status="queued_for_slot",
                priority=15,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            db.add(
                TransportQueue(
                    request_id=transport_req.id,
                    queue_type="WAITING_SLOT",
                    target_stage_level=0,
                    status="PENDING",
                    priority=15,
                )
            )

        db.commit()
        db.refresh(transport_req)
        return transport_req

    # =========================================================================
    # 7. FLEET TASK EXECUTION, WEBHOOK CALLBACKS & ALWAYS-SCAN QUEUE ENGINE
    # =========================================================================

    def _lock_cart_and_dispatch_fleet_task(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        """
        Atomically lock the container, set destination, create FleetTask in DB (Tx1 commit),
        and then dispatch submitMission to KUKA Fleet Manager (Tx2 commit).
        """
        mission_code = f"MS{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        fleet_req_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"

        # 1. Lock container immediately in MES DB (prevents any other machine from picking it)
        cart.is_locked = True
        cart.locked_by_mission_code = mission_code
        cart.destination_location_id = dropoff_location_id

        transport_req.container_id = cart.id
        transport_req.source_location_id = pickup_location_id
        transport_req.destination_location_id = dropoff_location_id
        transport_req.status = "in_progress"

        fleet_task = FleetTask(
            mission_code=mission_code,
            fleet_request_id=fleet_req_id,
            transport_request_id=transport_req.id,
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            container_id=cart.id,
            container_code=cart.container_code,
            status="pending_submit",
        )
        db.add(fleet_task)
        # Tx1 Commit: Task is securely persisted before calling Fleet (eliminates race condition with MOVE_BEGIN callback)
        db.commit()
        db.refresh(fleet_task)

        # 2. Call KUKA Fleet submitMission
        self.submit_fleet_task(db, fleet_task, request_type=transport_req.request_type)
        db.commit()
        db.refresh(fleet_task)
        return fleet_task

    def receive_task_status(self, db: Session, payload: dict[str, Any]) -> Optional[TaskStatus]:
        """
        Process incoming callback webhook from KUKA Fleet Manager (/api/v1/receive-status).
        1. Persists complete audit record in `task_status` (including raw_payload, coordinates, position).
        2. Acquires row lock (FOR UPDATE) on FleetTask by mission_code.
        3. Enforces strict state-machine (no backward state transitions):
           - MOVE_BEGIN / ARRIVED: AMR in-transit -> in_progress
           - UP_CONTAINER: AMR lifted container -> in_progress, confirm container locked
           - DOWN_CONTAINER: AMR put container down -> still in_progress (D2)
           - COMPLETED: Mission 100% finished -> marks completed, relocates container, unlocks, scans queues
           - FAILED / CANCELLED: Mission terminated -> unlocks container
        """
        mission_code = (
            payload.get("missionCode")
            or payload.get("mission_code")
            or payload.get("orderId")
        )
        if not mission_code:
            logger.warning("Fleet webhook missing missionCode in payload: %s", payload)
            return None

        mission_code_str = str(mission_code).strip()
        raw_status = str(payload.get("missionStatus") or payload.get("mission_status") or payload.get("status") or "").strip()
        robot_id = str(payload.get("robotId") or payload.get("robot_id") or payload.get("deviceCode") or "").strip() or None
        container_code = str(payload.get("containerCode") or payload.get("container_code") or payload.get("shelfNumber") or "").strip() or None
        location_code = str(payload.get("containerLocationCode") or "").strip() or None
        curr_pos = str(payload.get("currentPosition") or "").strip() or None
        map_code = str(payload.get("mapCode") or "").strip() or None
        org_id = str(payload.get("orgId") or "").strip() or None
        msg = str(payload.get("message") or "").strip() or None

        robot_x = None
        robot_y = None
        try:
            rx_val = payload.get("robotX")
            if rx_val not in ("", None):
                robot_x = float(rx_val)
            ry_val = payload.get("robotY")
            if ry_val not in ("", None):
                robot_y = float(ry_val)
        except (ValueError, TypeError):
            pass

        # 1. Audit log in task_status
        record = TaskStatus(
            mission_code=mission_code_str,
            mission_status=raw_status,
            robot_id=robot_id,
            container_code=container_code,
            container_location_code=location_code,
            current_position=curr_pos,
            robot_x=robot_x,
            robot_y=robot_y,
            org_id=org_id,
            map_code=map_code,
            message=msg,
            raw_payload=payload,
        )
        db.add(record)
        db.flush()

        # 2. Lock FleetTask by mission_code
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.mission_code == mission_code_str)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not fleet_task:
            logger.warning("Received status '%s' for unknown missionCode=%s", raw_status, mission_code_str)
            db.commit()
            db.refresh(record)
            return record

        # 3. Check for immutable final states (no backward transitions)
        if fleet_task.status in ("completed", "failed", "cancelled"):
            logger.info("FleetTask %s already in terminal state '%s', ignoring event '%s'", mission_code_str, fleet_task.status, raw_status)
            db.commit()
            db.refresh(record)
            return record

        fleet_task.last_mission_status = raw_status
        if curr_pos:
            fleet_task.current_position = curr_pos
        if robot_id:
            fleet_task.robot_id = robot_id

        # 4. State transition
        mapped_status = FLEET_MISSION_STATUS.get(raw_status) or MAPPING_STATUS.get(raw_status)

        if raw_status in ("MOVE_BEGIN", "ARRIVED"):
            fleet_task.status = "in_progress"
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            db.commit()

        elif raw_status == "UP_CONTAINER":
            fleet_task.status = "in_progress"
            fleet_task.picked_up_at = datetime.now(timezone.utc)
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            # Ensure container is locked
            if fleet_task.container_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    cart.is_locked = True
                    cart.locked_by_mission_code = mission_code_str
            db.commit()

        elif raw_status == "DOWN_CONTAINER":
            # D2: Still in_progress! Robot is putting container down, not finished yet
            fleet_task.status = "in_progress"
            db.commit()

        elif raw_status == "COMPLETED" or mapped_status == "completed":
            # D2: ONLY completion signal that finalizes mission
            db.commit()
            self.complete_fleet_task(db, mission_code_str)

        elif mapped_status in ("failed", "cancelled") or raw_status in ("FAILED", "CANCELLED", "CANCEL"):
            term_status = "cancelled" if "cancel" in raw_status.lower() else "failed"
            fleet_task.status = term_status
            fleet_task.error_message = msg or f"Fleet reported {raw_status}"
            if fleet_task.request:
                fleet_task.request.status = term_status
            if fleet_task.container_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.destination_location_id = None
            db.commit()
        else:
            db.commit()

        db.refresh(record)
        return record

    def complete_fleet_task(self, db: Session, mission_code: str) -> FleetTask:
        """
        Official completion handler when KUKA Fleet reports COMPLETED:
        1. If dropoff is at EMPTY_CART_BUFFER (or RETURN_EMPTY_CART):
           - Calls fleet_container_out to de-register container at Fleet.
           - Sets container location_id=None, is_active=False, status='empty'.
        2. Otherwise (CNC station or Washing slot):
           - Moves container.location_id to dropoff_location_id.
           - Clears container lock: is_locked=False, locked_by_mission_code=None.
        3. Marks FleetTask and TransportRequest completed.
        4. Scans TransportQueue (scan_all_transport_queues) to release next waiting workpiece.
        """
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.mission_code == mission_code)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not fleet_task:
            raise ValueError(f"Không tìm thấy FleetTask '{mission_code}'.")

        now = datetime.now(timezone.utc)
        fleet_task.status = "completed"
        fleet_task.completed_at = now

        req_type = None
        if fleet_task.request:
            req_type = fleet_task.request.request_type
            fleet_task.request.status = "completed"
            fleet_task.request.completed_at = now

        dropoff_loc = (
            db.query(Location).filter(Location.id == fleet_task.dropoff_location_id).first()
            if fleet_task.dropoff_location_id
            else None
        )
        is_empty_buffer_dropoff = bool(
            req_type == "RETURN_EMPTY_CART"
            or (dropoff_loc and dropoff_loc.location_type == "EMPTY_CART_BUFFER")
        )

        if fleet_task.container_id:
            cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
            if cart:
                if is_empty_buffer_dropoff:
                    if dropoff_loc and cart.container_code:
                        try:
                            self.fleet_container_out(location_code=dropoff_loc.location_code, container_code=cart.container_code, db=db)
                        except Exception as e:
                            logger.error("Could not call fleet_container_out: %s", e)
                    cart.location_id = None
                    cart.destination_location_id = None
                    cart.quantity = 0
                    cart.current_stage_level = 0
                    cart.status = "empty"
                    cart.is_active = False
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                else:
                    cart.location_id = fleet_task.dropoff_location_id
                    cart.destination_location_id = None
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.status = "available"

        db.commit()

        # Since pickup location is now free, immediately scan queues
        self.scan_all_transport_queues(db)
        return fleet_task

    def try_resolve_waiting_cart_queue(self, db: Session, stage_level: Optional[int] = None) -> int:
        """
        Scan `TransportQueue` (`WAITING_CART`) in FIFO order (`priority ASC, created_at ASC`).
        If `stage_level` is None, scans all pending `WAITING_CART` entries across all stage levels (Always Scan).
        If a cart is now available, lock it and dispatch a `FleetTask`.
        """
        query = db.query(TransportQueue).filter(
            TransportQueue.queue_type == "WAITING_CART",
            TransportQueue.status == "PENDING",
        )
        if stage_level is not None:
            query = query.filter(TransportQueue.target_stage_level == stage_level)

        pending_entries = (
            query.order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(of=TransportQueue, skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.item_id:
                continue
            if not self._is_location_free(db, req.destination_location_id):
                continue

            dest_loc = db.query(Location).filter(Location.id == req.destination_location_id).first()
            cart = self.find_fifo_available_cart(
                db,
                item_id=req.item_id,
                stage_level=req.required_stage_level,
                target_location=dest_loc,
            )
            if cart:
                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=req.destination_location_id,
                )
                entry.status = "RESOLVED"
                entry.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1

        if resolved_count:
            db.commit()
        return resolved_count

    def try_resolve_waiting_slot_queue(self, db: Session) -> int:
        """
        Scan `TransportQueue` (`WAITING_SLOT` / `WAITING_WASH_SLOT`) in FIFO order (`priority ASC, created_at ASC`).
        When a Washing slot or Empty Cart Buffer becomes free, dispatch the waiting cart.
        """
        pending_entries = (
            db.query(TransportQueue)
            .filter(
                TransportQueue.queue_type.in_(["WAITING_SLOT", "WAITING_WASH_SLOT"]),
                TransportQueue.status == "PENDING",
            )
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(of=TransportQueue, skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.container_id:
                continue

            cart = db.query(ItemStock).filter(ItemStock.id == req.container_id).first()
            if not cart or cart.is_locked or not cart.location_id:
                continue

            target_slot: Optional[Location] = None
            if req.request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
                target_slot = self.find_available_slot_to_wash(db)
            elif req.request_type == "RETURN_EMPTY_CART":
                target_slot = self.find_next_empty_buffer_slot(db)

            if target_slot:
                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=target_slot.id,
                )
                entry.status = "RESOLVED"
                entry.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1

        if resolved_count:
            db.commit()
        return resolved_count

    def scan_all_transport_queues(self, db: Session) -> dict[str, int]:
        """
        [ALWAYS SCAN ENGINE]
        Sweeps all pending `WAITING_CART` entries (across all stage levels) and all pending
        `WAITING_SLOT` entries to automatically match available carts and freed slots.
        Called both reactively on events and periodically via Celery Beat.
        """
        resolved_carts = self.try_resolve_waiting_cart_queue(db, stage_level=None)
        resolved_slots = self.try_resolve_waiting_slot_queue(db)
        return {
            "resolved_waiting_cart": resolved_carts,
            "resolved_waiting_slot": resolved_slots,
        }


dispatch_service = DispatchService()
