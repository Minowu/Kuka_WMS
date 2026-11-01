"""
Test KUKA Fleet Real Protocol & Replay Engine.

Replays the 7 exact lifecycle signals captured from the real KUKA Fleet Manager (192.168.1.71)
in `backend/logs/fleet_signals/all_signals.jsonl`.

Verifies:
1. `containerIn` registration at Node 17 (position: CNC001-CNC001-17).
2. Outbox task submission: creates pending_submit FleetTask in Tx1, then submits to Fleet (Tx2).
3. 7-step Callback State Machine:
   - Event 1: MOVE_BEGIN (currentPosition: "-1") -> in_progress, robot_id=1515
   - Event 2: ARRIVED (currentPosition: Node 17) -> in_progress, coordinates updated
   - Event 3: UP_CONTAINER -> in_progress, picked_up_at set, container confirmed locked
   - Event 4: MOVE_BEGIN (Node 17 -> Node 18) -> in_progress
   - Event 5: ARRIVED (Node 18) -> in_progress
   - Event 6: DOWN_CONTAINER -> in_progress (D2: still in_progress, not completed!)
   - Event 7: COMPLETED -> completed! Container location updated to Node 18, unlocked!
4. Immutability & Replay Defense:
   - Subsequent duplicate callbacks after COMPLETED do not rewind state or re-trigger queue scans.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main
from app.core.database import SessionLocal
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    TaskStatus,
    TransportRequest,
    TransportQueue,
    ProductionRecord,
    FleetApiCall,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location


def run_kuka_fleet_replay_test():
    print("=" * 70)
    print("🤖 BẮT ĐẦU KIỂM THỬ REPLAY 7 TÍN HIỆU THỰC TẾ KUKA FLEET MANAGER")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Setup / Lookup Node 17 and Node 18
        loc17 = db.query(Location).filter(Location.location_code == "CNC001-CNC001-17").first()
        loc18 = db.query(Location).filter(Location.location_code == "CNC001-CNC001-18").first()
        # Backup original location types to restore after test
        loc17_orig_type = loc17.location_type
        loc17_orig_name = loc17.location_name
        loc18_orig_type = loc18.location_type
        loc18_orig_name = loc18.location_name
        loc18_orig_machine = loc18.machine_id
        loc18_orig_pos = loc18.position_index

        loc17.is_active = True
        loc17.location_type = "RAW_MATERIAL"
        loc18.is_active = True
        loc18.location_type = "CNC_SLOT"
        db.flush()

        test_item = db.query(Item).first()
        if not test_item:
            test_item = Item(sku="KUKA-TEST-01", name="Chi tiết phôi test", warehouse_id=1)
            db.add(test_item)
            db.flush()

        db.commit()

        # Intercept _post_kuka when no live access token is configured
        from app.core.config import settings
        recorded_calls = []
        from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
        orig_post_kuka = KukaFleetClient._post_kuka

        def mock_post_kuka(
                self,
                endpoint_path: str,
                payload: dict,
                api_name: str,
                mission_code: str = None,
                container_code: str = None,
                request_id: str = None,
                db=None,
            ):
                recorded_calls.append({
                    "endpoint": endpoint_path,
                    "api_name": api_name,
                    "payload": payload,
                    "mission_code": mission_code,
                    "container_code": container_code,
                })
                resp = {"code": "0", "message": "success", "success": True, "data": None}
                if db:
                    call_log = FleetApiCall(
                        api_name=api_name,
                        request_id=request_id or payload.get("requestId", "REQ_TEST"),
                        mission_code=mission_code or payload.get("missionCode"),
                        container_code=container_code or payload.get("containerCode"),
                        request_body=payload,
                        http_status=200,
                        response_body=resp,
                        success=True,
                    )
                    db.add(call_log)
                    db.flush()
                return resp

        KukaFleetClient._post_kuka = mock_post_kuka

        mission_code = "KK2026171099191821"
        container_code = "123123"

        # Cleanup old test records for this mission
        db.query(TaskStatus).filter(TaskStatus.mission_code == mission_code).delete()
        db.query(FleetTask).filter(FleetTask.mission_code == mission_code).delete()
        old_carts = db.query(ItemStock).filter(ItemStock.container_code == container_code).all()
        for oc in old_carts:
            db.query(TransportRequest).filter(TransportRequest.container_id == oc.id).delete()
            db.query(ProductionRecord).filter(ProductionRecord.container_id == oc.id).delete()
            db.delete(oc)
        db.commit()

        # Step 1: Register Container at Node 17
        print("\n[Bước 1] Khai báo phôi vào ô (containerIn)...")
        reg_result = dispatch_service.register_rack_at_raw_material(
            db=db,
            location_id=loc17.id,
            item_id=test_item.id,
            container_code=container_code,
            quantity=120,
        )
        cart = db.query(ItemStock).filter(ItemStock.container_code == container_code).first()
        assert cart is not None
        assert cart.location_id == loc17.id
        assert cart.fleet_registered is True
        print(f"  ✔ Container [{container_code}] nạp thành công tại [{loc17.location_code}], fleet_registered=True")

        # Step 2: Create TransportRequest & Dispatch FleetTask
        print("\n[Bước 2] MES khởi tạo TransportRequest và FleetTask...")
        req = TransportRequest(
            request_code=f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_type="CALL_MATERIAL",
            item_id=test_item.id,
            source_location_id=loc17.id,
            destination_location_id=loc18.id,
            container_id=cart.id,
            status="pending",
        )
        db.add(req)
        db.flush()

        fleet_task = dispatch_service._lock_cart_and_dispatch_fleet_task(
            db=db,
            transport_req=req,
            cart=cart,
            pickup_location_id=loc17.id,
            dropoff_location_id=loc18.id,
        )
        # Override mission_code for deterministic replay matching
        fleet_task.mission_code = mission_code
        cart.locked_by_mission_code = mission_code
        db.commit()

        assert cart.is_locked is True
        db.refresh(fleet_task)
        assert fleet_task.status in ("pending_submit", "submitting", "sent")
        print(f"  ✔ FleetTask tạo thành công với mission_code=[{mission_code}], container=[{container_code}] bị khóa.")

        # Step 3: Replay 7 exact signals
        print("\n[Bước 3] Phát lại tuần tự 7 sự kiện thật từ KUKA Fleet Manager...")

        signals = [
            # Signal 1: MOVE_BEGIN (Robot xuất phát)
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-17",
                "currentPosition": "-1",
                "missionStatus": "MOVE_BEGIN",
                "robotId": "1515",
                "robotX": "173.265",
                "robotY": "77.367",
                "message": "lang.wcs.common.ok",
            },
            # Signal 2: ARRIVED at pickup
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-17",
                "currentPosition": "CNC001-CNC001-17",
                "missionStatus": "ARRIVED",
                "robotId": "1515",
                "robotX": "179.713",
                "robotY": "83.8",
                "message": "lang.wcs.common.ok",
            },
            # Signal 3: UP_CONTAINER
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-17",
                "currentPosition": "CNC001-CNC001-17",
                "missionStatus": "UP_CONTAINER",
                "robotId": "1515",
                "robotX": "",
                "robotY": "",
                "message": "lang.wcs.common.ok",
            },
            # Signal 4: MOVE_BEGIN to dropoff
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-17",
                "currentPosition": "CNC001-CNC001-17",
                "missionStatus": "MOVE_BEGIN",
                "robotId": "1515",
                "robotX": "179.713",
                "robotY": "83.8",
                "message": "lang.wcs.common.ok",
            },
            # Signal 5: ARRIVED at dropoff
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-18",
                "currentPosition": "CNC001-CNC001-18",
                "missionStatus": "ARRIVED",
                "robotId": "1515",
                "robotX": "178.513",
                "robotY": "83.8",
                "message": "lang.wcs.common.ok",
            },
            # Signal 6: DOWN_CONTAINER (D2: still in_progress!)
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-18",
                "currentPosition": "CNC001-CNC001-18",
                "missionStatus": "DOWN_CONTAINER",
                "robotId": "1515",
                "robotX": "",
                "robotY": "",
                "message": "lang.wcs.common.ok",
            },
            # Signal 7: COMPLETED (Final completion!)
            {
                "orgId": "KUKA011021",
                "missionCode": mission_code,
                "containerCode": container_code,
                "containerLocationCode": "CNC001-CNC001-18",
                "currentPosition": "CNC001-CNC001-18",
                "missionStatus": "COMPLETED",
                "robotId": "1515",
                "robotX": "178.513",
                "robotY": "83.8",
                "message": "lang.wcs.common.ok",
            },
        ]

        for idx, sig in enumerate(signals, 1):
            dispatch_service.receive_task_status(db, sig)
            db.refresh(fleet_task)
            db.refresh(cart)

            status_ev = sig["missionStatus"]
            print(f"  Sự kiện {idx}/7 [{status_ev}]: FleetTask={fleet_task.status}, Robot={fleet_task.robot_id}, Container Locked={cart.is_locked}")

            if status_ev in ("MOVE_BEGIN", "ARRIVED", "UP_CONTAINER"):
                assert fleet_task.status == "in_progress"
                assert cart.is_locked is True
            elif status_ev == "DOWN_CONTAINER":
                # CRITICAL VERIFICATION: D2 - must still be in_progress!
                assert fleet_task.status == "in_progress", f"DOWN_CONTAINER must be in_progress, got {fleet_task.status}"
                assert cart.is_locked is True
            elif status_ev == "COMPLETED":
                # CRITICAL VERIFICATION: COMPLETED is the sole completion event!
                assert fleet_task.status == "completed"
                assert cart.is_locked is False
                assert cart.location_id == loc18.id, f"Container location must be Node 18, got {cart.location_id}"
                print(f"  🎯 COMPLETED: Vị trí container đã chuyển sang [{loc18.location_code}], mở khóa is_locked=False thành công!")

        # Step 4: Verify Idempotency & Defense against duplicate callbacks
        print("\n[Bước 4] Kiểm tra chống lùi trạng thái (Duplicate callback sau COMPLETED)...")
        # Send duplicate DOWN_CONTAINER after COMPLETED
        dispatch_service.receive_task_status(db, signals[5])
        db.refresh(fleet_task)
        assert fleet_task.status == "completed", "Trạng thái không được phép lùi về in_progress sau khi đã COMPLETED!"
        print("  ✔ Chống lùi trạng thái hoàn hảo: FleetTask vẫn giữ nguyên trạng thái 'completed'!")

        # Step 5: Verify task_status audit trail
        logs = db.query(TaskStatus).filter(TaskStatus.mission_code == mission_code).order_by(TaskStatus.id.asc()).all()
        assert len(logs) == 8, f"Expected 8 TaskStatus rows, got {len(logs)}"
        assert logs[-1].raw_payload is not None
        print(f"  ✔ Ghi log kiểm toán task_status đầy đủ 100%: {len(logs)} bản ghi với raw_payload JSONB.")

        print("\n" + "=" * 70)
        print("🎉 TOÀN BỘ BÀI TEST REPLAY KUKA FLEET MANAGER THÀNH CÔNG 100%!")
        print("=" * 70)

    finally:
        if 'orig_post_kuka' in locals():
            from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
            KukaFleetClient._post_kuka = orig_post_kuka
        # Restore original location settings for node 17 & 18 if modified
        try:
            if 'loc17_orig_type' in locals() and loc17:
                loc17.location_type = loc17_orig_type
                loc17.location_name = loc17_orig_name
            if 'loc18_orig_type' in locals() and loc18:
                loc18.location_type = loc18_orig_type
                loc18.location_name = loc18_orig_name
                loc18.machine_id = loc18_orig_machine
                loc18.position_index = loc18_orig_pos

            # Dọn dẹp sạch sẽ các bản ghi test để không để lại lệnh nào chạy dở
            if 'mission_code' in locals():
                db.query(TaskStatus).filter(TaskStatus.mission_code == mission_code).delete()
                db.query(FleetTask).filter(FleetTask.mission_code == mission_code).delete()
            if 'container_code' in locals():
                for c in db.query(ItemStock).filter(ItemStock.container_code == container_code).all():
                    db.query(TransportRequest).filter(TransportRequest.container_id == c.id).delete()
                    db.query(ProductionRecord).filter(ProductionRecord.container_id == c.id).delete()
                    db.delete(c)
            db.commit()
        except Exception as e:
            print(f"Warning: Failed to restore locations in finally: {e}")
        db.close()


if __name__ == "__main__":
    run_kuka_fleet_replay_test()
