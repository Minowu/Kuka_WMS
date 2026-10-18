"""
End-to-End Verification Script for CNC Production & KUKA AMR Dispatch Engine (3NF).

Verifies:
1. User Location Assignment Constraint (Max 3 locations per user).
2. Scenario 1 & 2 (FIFO Cart Selection + POS1/POS2 Buffering at CNC-01).
3. Scenario 3 (Multi-Stage Progression Level 1 -> Level 2 -> Level 3 -> Washing -> Empty Cart Return).
4. Queueing (`TransportQueue` WAITING_CART) & Raw Material Rack QR Registration (`register_rack_at_raw_material` reusing rack QR + auto-dispatching to waiting CNC).
5. KUKA Fleet Webhook Callback (`receive_task_status` -> `TaskStatus` + `FleetTask` + `ItemStock` settlement).
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.auth.auth_model import User
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    RouteStepMachine,
    TaskStatus,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from scripts.seed_production_core import seed_production_core


def reset_runtime_tables(db) -> None:
    """Clear runtime dispatch tables before running deterministic test scenarios."""
    db.query(TaskStatus).delete()
    db.query(ProductionRecord).delete()
    db.query(FleetTask).delete()
    db.query(TransportQueue).delete()
    db.query(TransportRequest).delete()
    db.query(UserLocation).delete()
    db.commit()


def run_verification() -> None:
    print("🚀 Bắt đầu kiểm thử End-to-End Dispatch Engine (3NF + Fleet Webhook + Rack QR)...")
    db = SessionLocal()
    try:
        reset_runtime_tables(db)
    finally:
        db.close()

    seed_production_core()

    db = SessionLocal()
    try:
        # Verify 3NF Machine & RouteStepMachine tables
        machine_count = db.query(Machine).count()
        step_machine_count = db.query(RouteStepMachine).count()
        assert machine_count >= 4, f"Expected >= 4 Machine rows, got {machine_count}"
        assert step_machine_count >= 5, f"Expected >= 5 RouteStepMachine rows, got {step_machine_count}"
        print(f"  ✔ [Test 0] Chuẩn hóa 3NF thành công: {machine_count} Machines, {step_machine_count} RouteStepMachine links!")

        # Lookup seeded entities
        model_a = db.query(Item).filter(Item.sku == "MODEL-A").first()
        model_b = db.query(Item).filter(Item.sku == "MODEL-B").first()
        cnc01_pos1 = db.query(Location).filter(Location.location_code == "CNC-01-POS1").first()
        cnc01_pos2 = db.query(Location).filter(Location.location_code == "CNC-01-POS2").first()
        cnc02_pos1 = db.query(Location).filter(Location.location_code == "CNC-02-POS1").first()
        raw03 = db.query(Location).filter(Location.location_code == "RAW-03").first()

        # ---------------------------------------------------------------------
        # TEST 1: User Location Constraint (Max 3 locations per operator)
        # ---------------------------------------------------------------------
        user = db.query(User).first()
        if user:
            all_locs = db.query(Location).limit(4).all()
            if len(all_locs) >= 4:
                try:
                    dispatch_service.assign_locations_to_user(
                        db, user.id, [loc.id for loc in all_locs[:4]]
                    )
                    raise AssertionError("Expected ValueError when assigning 4 locations to a user!")
                except ValueError as e:
                    print(f"  ✔ [Test 1a] Chặn gán >3 vị trí thành công: {e}")

                assigned = dispatch_service.assign_locations_to_user(
                    db, user.id, [loc.id for loc in all_locs[:3]]
                )
                assert len(assigned) == 3
                print("  ✔ [Test 1b] Gán 3 vị trí hợp lệ cho User thành công!")

        # ---------------------------------------------------------------------
        # TEST 2: FIFO Cart Selection & POS1 / POS2 Buffering at CNC-01
        # ---------------------------------------------------------------------
        req1 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc01_pos1.id, item_id=model_a.id
        )
        cart1 = db.query(ItemStock).filter(ItemStock.id == req1.cart_id).first()
        assert cart1.cart_code == "CART-001", f"Expected FIFO CART-001, got {cart1.cart_code}"
        assert cart1.is_locked is True
        assert req1.destination_location_id == cnc01_pos1.id
        print(f"  ✔ [Test 2a] Chọn xe FIFO chính xác: {cart1.cart_code} -> CNC-01-POS1 (Locked={cart1.is_locked})")

        # Call material again targeting CNC-01-POS1 while POS1 is already reserved -> auto fallback to POS2!
        req2 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc01_pos1.id, item_id=model_a.id
        )
        cart2 = db.query(ItemStock).filter(ItemStock.id == req2.cart_id).first()
        assert cart2.cart_code == "CART-002", f"Expected second FIFO CART-002, got {cart2.cart_code}"
        assert req2.destination_location_id == cnc01_pos2.id, "Expected automatic fallback to CNC-01-POS2!"
        print(f"  ✔ [Test 2b] Tự động điều hướng sang vị trí đệm dự phòng: {cart2.cart_code} -> CNC-01-POS2")

        # Simulate KUKA Fleet Webhook (/receive-status) for both deliveries (status="8" -> completed)
        task1 = db.query(FleetTask).filter(FleetTask.request_id == req1.id).first()
        task2 = db.query(FleetTask).filter(FleetTask.request_id == req2.id).first()
        dispatch_service.receive_task_status(
            db,
            {"orderId": task1.task_code, "status": "6", "deviceCode": "KUKA-AMR-01"},
        )
        dispatch_service.receive_task_status(
            db,
            {"orderId": task1.task_code, "status": "8", "deviceCode": "KUKA-AMR-01", "shelfNumber": "CART-001"},
        )
        dispatch_service.receive_task_status(
            db,
            {"orderId": task2.task_code, "status": "8", "deviceCode": "KUKA-AMR-02", "shelfNumber": "CART-002"},
        )

        db.refresh(cart1)
        db.refresh(cart2)
        assert cart1.location_id == cnc01_pos1.id and cart1.is_locked is False
        assert cart2.location_id == cnc01_pos2.id and cart2.is_locked is False
        status_logs = db.query(TaskStatus).filter(TaskStatus.order_id == task1.task_code).count()
        assert status_logs == 2
        print("  ✔ [Test 2c] Webhook /receive-status lưu TaskStatus và cập nhật vị trí + mở khóa xe thành công!")

        # ---------------------------------------------------------------------
        # TEST 3: Multi-Stage Progression (Level 1 -> Level 2 -> Level 3 -> Washing -> Empty Return)
        # ---------------------------------------------------------------------
        res_lvl1 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl1["completed_stage_level"] == 1
        assert res_lvl1["action"] == "DISPATCHED_TO_NEXT_STAGE"
        task_lvl2 = (
            db.query(FleetTask)
            .join(TransportRequest, FleetTask.request_id == TransportRequest.id)
            .filter(TransportRequest.request_code == res_lvl1["request_code"])
            .first()
        )
        dispatch_service.receive_task_status(db, {"orderId": task_lvl2.task_code, "status": "8"})
        db.refresh(cart1)
        loc_lvl2 = db.query(Location).filter(Location.id == cart1.location_id).first()
        assert loc_lvl2.machine_code == "CNC-03"
        print(f"  ✔ [Test 3a] Hoàn thành Level 1 -> Tự động chuyển sang {loc_lvl2.location_code} (Level 2)")

        res_lvl2 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl2["completed_stage_level"] == 2
        assert res_lvl2["action"] == "DISPATCHED_TO_NEXT_STAGE"
        task_lvl3 = (
            db.query(FleetTask)
            .join(TransportRequest, FleetTask.request_id == TransportRequest.id)
            .filter(TransportRequest.request_code == res_lvl2["request_code"])
            .first()
        )
        dispatch_service.receive_task_status(db, {"orderId": task_lvl3.task_code, "status": "8"})
        db.refresh(cart1)
        loc_lvl3 = db.query(Location).filter(Location.id == cart1.location_id).first()
        assert loc_lvl3.machine_code == "CNC-04"
        print(f"  ✔ [Test 3b] Hoàn thành Level 2 -> Tự động chuyển sang {loc_lvl3.location_code} (Level 3)")

        res_lvl3 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl3["completed_stage_level"] == 3
        assert res_lvl3["action"] == "DISPATCHED_TO_WASHING"
        task_wash = (
            db.query(FleetTask)
            .join(TransportRequest, FleetTask.request_id == TransportRequest.id)
            .filter(TransportRequest.request_code == res_lvl3["request_code"])
            .first()
        )
        dispatch_service.receive_task_status(db, {"orderId": task_wash.task_code, "status": "8"})
        db.refresh(cart1)
        loc_wash = db.query(Location).filter(Location.id == cart1.location_id).first()
        assert loc_wash.location_type == "WASHING_SLOT"
        print(f"  ✔ [Test 3c] Hoàn thành Level 3 (Final CNC) -> Tự động chuyển sang Trạm Rửa ({loc_wash.location_code})")

        req_empty = dispatch_service.complete_washing_and_return_empty_cart(db, cart_code="CART-001")
        task_empty = db.query(FleetTask).filter(FleetTask.request_id == req_empty.id).first()
        dispatch_service.receive_task_status(db, {"orderId": task_empty.task_code, "status": "8"})
        db.refresh(cart1)
        loc_empty = db.query(Location).filter(Location.id == cart1.location_id).first()
        assert loc_empty.location_type == "EMPTY_CART_BUFFER"
        assert cart1.quantity == 0
        print(f"  ✔ [Test 3d] Hoàn thành Rửa -> Tự động trả xe rỗng về ({loc_empty.location_code}, quantity={cart1.quantity})")

        # ---------------------------------------------------------------------
        # TEST 4: Queueing (WAITING_CART) & Raw Material Reusable Rack QR Registration
        # ---------------------------------------------------------------------
        # Both CART-001 and CART-002 are no longer at RAW_MATERIAL.
        # Calling MODEL-A to CNC-02-POS1 now must enter WAITING_CART queue!
        req_queued = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc02_pos1.id, item_id=model_a.id
        )
        assert req_queued.status == "queued_for_cart"
        q_entry = (
            db.query(TransportQueue)
            .filter(TransportQueue.request_id == req_queued.id)
            .first()
        )
        assert q_entry is not None and q_entry.status == "PENDING"
        print(f"  ✔ [Test 4a] Hết phôi MODEL-A -> Tự động đưa yêu cầu {req_queued.request_code} vào TransportQueue (WAITING_CART)")

        # Now operator brings empty rack CART-001 back to RAW-01, selects MODEL-A, and scans QR CART-001!
        raw01 = db.query(Location).filter(Location.location_code == "RAW-01").first()
        reg_res = dispatch_service.register_rack_at_raw_material(
            db=db,
            location_id=raw01.id,
            item_id=model_a.id,
            cart_code="CART-001",
        )
        assert reg_res["fleet_inserted"] is True
        assert reg_res["resolved_queue_count"] == 1
        assert reg_res["is_locked"] is True
        assert reg_res["dispatched_task_code"] is not None

        db.refresh(q_entry)
        db.refresh(req_queued)
        assert q_entry.status == "RESOLVED"
        assert req_queued.status == "in_progress"
        print(
            f"  ✔ [Test 4b] Quét QR tái sử dụng rack CART-001 tại RAW-01 -> Tự động gửi POST insert Fleet & giải phóng Queue ({reg_res['dispatched_task_code']})!"
        )

        print("\n🎉 TẤT CẢ CÁC KỊCH BẢN KIỂM THỬ ĐỀU VƯỢT QUA 100%!")
    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
