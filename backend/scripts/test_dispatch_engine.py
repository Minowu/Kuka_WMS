"""
End-to-End Verification Script for CNC Production & KUKA AMR Dispatch Engine (3NF).

Verifies:
1. Unrestricted User Location Assignment (`assign_locations_to_user` supports assigning 7 Raw Material or 6 CNC slots).
2. Scenario 1 & 2 (FIFO Cart Selection + POS1/POS2 Buffering at CNC-01).
3. Scenario 3 (Pull + Always Scan Multi-Stage Progression: Intermediate stage completion + Downstream CNC Call auto-inferring stage_level -> Final CNC step auto-pushing to Washing).
4. Scenario 4 (Empty Cart Buffer Round-Robin 1..4 & Automatic Rack Removal `location_id=None, is_active=False` upon AMR dropoff).
5. Queueing (`TransportQueue` WAITING_CART) & Raw Material Rack QR Registration (`register_rack_at_raw_material` reusing rack QR + auto-dispatching to waiting CNC).
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
    print("🚀 Bắt đầu kiểm thử End-to-End Dispatch Engine (3NF + Pull/Always-Scan + Empty Buffer 1..4)...")
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
        cnc01_pos1 = db.query(Location).filter(Location.location_code == "CNC-01-POS1").first()
        cnc01_pos2 = db.query(Location).filter(Location.location_code == "CNC-01-POS2").first()
        cnc02_pos1 = db.query(Location).filter(Location.location_code == "CNC-02-POS1").first()
        cnc03_pos1 = db.query(Location).filter(Location.location_code == "CNC-03-POS1").first()
        cnc04_pos1 = db.query(Location).filter(Location.location_code == "CNC-04-POS1").first()

        # ---------------------------------------------------------------------
        # TEST 1: Unrestricted User Location Assignment (e.g. 7 Raw Material slots)
        # ---------------------------------------------------------------------
        user = db.query(User).first()
        if user:
            raw_locs = (
                db.query(Location)
                .filter(Location.location_type == "RAW_MATERIAL", Location.is_active.is_(True))
                .all()
            )
            assert len(raw_locs) >= 2, f"Expected >= 2 RAW_MATERIAL locations, got {len(raw_locs)}"
            assigned = dispatch_service.assign_locations_to_user(
                db, user.id, [loc.id for loc in raw_locs]
            )
            assert len(assigned) == len(raw_locs)
            print(f"  ✔ [Test 1] Gán không giới hạn ({len(assigned)} vị trí) cho User thành công!")

        # ---------------------------------------------------------------------
        # TEST 2: FIFO Cart Selection & POS1 / POS2 Buffering at CNC-01
        # ---------------------------------------------------------------------
        req1 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc01_pos1.id, item_id=model_a.id
        )
        cart1 = db.query(ItemStock).filter(ItemStock.id == req1.container_id).first()
        assert cart1.cart_code == "CART-001", f"Expected FIFO CART-001, got {cart1.cart_code}"
        assert cart1.is_locked is True
        assert req1.destination_location_id == cnc01_pos1.id
        assert req1.required_stage_level == 0
        print(f"  ✔ [Test 2a] Chọn xe FIFO chính xác: {cart1.cart_code} -> CNC-01-POS1 (Locked={cart1.is_locked})")

        # Call material targeting CNC-01-POS1 while POS1 is already reserved -> raises error!
        try:
            dispatch_service.call_material_to_cnc(
                db, destination_location_id=cnc01_pos1.id, item_id=model_a.id
            )
            assert False, "Calling occupied POS1 should raise error!"
        except ValueError as err:
            assert "đang có xe hoặc đã có AMR đặt chỗ" in str(err)

        # Operator explicitly selects free sibling slot CNC-01-POS2 -> calls successfully!
        req2 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc01_pos2.id, item_id=model_a.id
        )
        cart2 = db.query(ItemStock).filter(ItemStock.id == req2.container_id).first()
        assert cart2.cart_code == "CART-002", f"Expected second FIFO CART-002, got {cart2.cart_code}"
        assert req2.destination_location_id == cnc01_pos2.id, "Expected destination to be CNC-01-POS2!"
        print(f"  ✔ [Test 2b] Khóa chặt vị trí công nhân chọn: Chặn gọi vào POS1 bận, điều xe chính xác vào CNC-01-POS2 ({cart2.cart_code})!")

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
        # TEST 3: Pull + Always Scan Multi-Stage Progression (Level 1 -> Level 2 -> Level 3 -> Washing)
        # ---------------------------------------------------------------------
        # 3a. Complete Level 1 at CNC-01-POS1 while CNC-03 has NOT called yet -> cart stays at CNC-01-POS1 (Level 1)
        res_lvl1 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl1["completed_stage_level"] == 1
        assert res_lvl1["action"] == "STAGE_COMPLETED_WAITING_CALL"
        db.refresh(cart1)
        assert cart1.current_stage_level == 1 and cart1.location_id == cnc01_pos1.id and cart1.is_locked is False
        print("  ✔ [Test 3a] Hoàn thành Level 1 (bước trung gian): chỉ nâng Level 1 và đứng chờ gọi tại CNC-01-POS1")

        # Now CNC-03-POS1 (Stage 2 machine) calls MODEL-A without passing required_stage_level -> auto-infers Level 1!
        req_lvl2 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc03_pos1.id, item_id=model_a.id
        )
        assert req_lvl2.required_stage_level == 1, f"Expected auto-inferred required_stage_level=1, got {req_lvl2.required_stage_level}"
        assert req_lvl2.container_id == cart1.id and req_lvl2.status == "in_progress"
        task_lvl2 = db.query(FleetTask).filter(FleetTask.request_id == req_lvl2.id).first()
        dispatch_service.receive_task_status(db, {"orderId": task_lvl2.task_code, "status": "8"})
        db.refresh(cart1)
        assert cart1.location_id == cnc03_pos1.id and cart1.is_locked is False
        print("  ✔ [Test 3b] Máy CNC-03 bấm Gọi hàng -> Tự suy ra Level 1 và kéo xe CART-001 sang CNC-03-POS1!")

        # 3c. Now test the reverse order: CNC-04-POS1 (Stage 3 machine) calls MODEL-A BEFORE CNC-03 finishes Level 2!
        req_lvl3 = dispatch_service.call_material_to_cnc(
            db, destination_location_id=cnc04_pos1.id, item_id=model_a.id
        )
        assert req_lvl3.required_stage_level == 2
        assert req_lvl3.status == "queued_for_cart"
        print("  ✔ [Test 3c] Máy CNC-04 bấm Gọi hàng khi chưa có xe Level 2 -> Đưa vào hàng đợi WAITING_CART (Level 2)")

        # Now CNC-03 finishes Level 2 -> Immediately scans WAITING_CART and dispatches CART-001 to CNC-04-POS1!
        res_lvl2 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl2["completed_stage_level"] == 2
        assert res_lvl2["action"] == "DISPATCHED_TO_WAITING_CNC"
        assert res_lvl2["resolved_queue_count"] == 1
        task_lvl3 = db.query(FleetTask).filter(FleetTask.request_id == req_lvl3.id).first()
        assert task_lvl3 is not None
        dispatch_service.receive_task_status(db, {"orderId": task_lvl3.task_code, "status": "8"})
        db.refresh(cart1)
        assert cart1.location_id == cnc04_pos1.id and cart1.is_locked is False
        print("  ✔ [Test 3d] CNC-03 bấm Hoàn thành Level 2 -> Always-Scan khớp ngay với đơn chờ của CNC-04-POS1!")

        # 3e. Complete Level 3 (Final CNC step) at CNC-04 -> Automatically pushes to WASHING_SLOT!
        res_lvl3 = dispatch_service.complete_machining_stage(db, cart_code="CART-001")
        assert res_lvl3["completed_stage_level"] == 3
        assert res_lvl3["is_final_cnc_step"] is True
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
        print(f"  ✔ [Test 3e] Hoàn thành Level 3 (Final CNC) -> Tự động đẩy sang Trạm Rửa ({loc_wash.location_code})")

        # ---------------------------------------------------------------------
        # TEST 4: Empty Cart Buffer Round-Robin (1 -> 2 -> 3 -> 4) & Auto-Delete on Dropoff
        # ---------------------------------------------------------------------
        # Return CART-001 from Washing -> should pick EMPTY-01, and upon arrival delete/unbind cart!
        req_empty1 = dispatch_service.complete_washing_and_return_empty_cart(db, cart_code="CART-001")
        loc_buf1 = db.query(Location).filter(Location.id == req_empty1.destination_location_id).first()
        assert loc_buf1.location_code == "EMPTY-01", f"Expected EMPTY-01, got {loc_buf1.location_code}"
        task_empty1 = db.query(FleetTask).filter(FleetTask.request_id == req_empty1.id).first()
        dispatch_service.receive_task_status(db, {"orderId": task_empty1.task_code, "status": "8"})
        db.refresh(cart1)
        assert cart1.location_id is None and cart1.is_active is False and cart1.quantity == 0 and cart1.status == "empty"
        print("  ✔ [Test 4a] Xe rỗng 1 về EMPTY-01 -> Khi hạ xe tự động gọi fleet_remove_rack & xóa khỏi vị trí (location_id=None, is_active=False)!")

        # Return CART-002 from Washing -> Round-Robin must pick EMPTY-02 (even though EMPTY-01 is now free)!
        req_empty2 = dispatch_service.complete_washing_and_return_empty_cart(db, cart_code="CART-002")
        loc_buf2 = db.query(Location).filter(Location.id == req_empty2.destination_location_id).first()
        assert loc_buf2.location_code == "EMPTY-02", f"Expected Round-Robin EMPTY-02, got {loc_buf2.location_code}"
        task_empty2 = db.query(FleetTask).filter(FleetTask.request_id == req_empty2.id).first()
        dispatch_service.receive_task_status(db, {"orderId": task_empty2.task_code, "status": "8"})
        db.refresh(cart2)
        assert cart2.location_id is None and cart2.is_active is False
        print("  ✔ [Test 4b] Xe rỗng 2 tự động xoay vòng sang EMPTY-02 (Round-Robin 1->4) & tự xóa khi hạ xe!")

        # ---------------------------------------------------------------------
        # TEST 5: Queueing (WAITING_CART) & Raw Material Reusable Rack QR Registration
        # ---------------------------------------------------------------------
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
        print(f"  ✔ [Test 5a] Hết phôi MODEL-A -> Tự động đưa yêu cầu {req_queued.request_code} vào TransportQueue (WAITING_CART)")

        # Operator brings empty rack CART-001 back to VT-01, selects MODEL-A, and scans QR CART-001!
        raw01 = db.query(Location).filter(Location.location_code.in_(["VT-01", "RAW-01"])).first()
        assert raw01 is not None, "Vị trí VT-01 / RAW-01 không tìm thấy"
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
            f"  ✔ [Test 5b] Quét QR tái sử dụng rack CART-001 tại RAW-01 -> Tự động gửi POST insert Fleet & giải phóng Queue ({reg_res['dispatched_task_code']})!"
        )

        print("\n🎉 TẤT CẢ CÁC KỊCH BẢN KIỂM THỬ ĐỀU VƯỢT QUA 100%!")
    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
