"""Test script for KUKA AMR Dispatch Engine.

Verifies:
1. Euclidean distance calculation and nearest cart selection.
2. Material request dispatching and cart locking.
3. Intermediate stage completion and automated queue resolution.
4. Final stage completion and automatic washing transfer.
5. Wash slot release and empty cart return to buffer.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.modules.auth.auth_model import User
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.item.item_model import Item
from app.modules.production.production_models import (
    TransportRequest,
    TransportQueue,
    FleetTask,
    ProductionRecord,
)
from app.modules.production.dispatch_service import DispatchService


def run_tests():
    db: Session = SessionLocal()
    try:
        # Reset state for idempotent test runs
        vt1 = db.query(Location).filter(Location.location_code == "VT-01").first()
        rck1 = db.query(ItemStock).filter(ItemStock.cart_code == "RCK-VT01-1021").first()
        if vt1 and rck1:
            rck1.location_id = vt1.id
            rck1.current_stage_level = 0
            rck1.is_locked = False
            rck1.locked_by_task_id = None
            rck1.destination_location_id = None
            rck1.status = "available"
            db.commit()

        cnc4 = db.query(Location).filter(Location.location_code == "CNC04_POS1").first()
        rck4 = db.query(ItemStock).filter(ItemStock.cart_code == "RCK-CNC04-4101").first()
        if cnc4 and rck4:
            rck4.location_id = cnc4.id
            rck4.current_stage_level = 3
            rck4.is_locked = False
            rck4.locked_by_task_id = None
            rck4.destination_location_id = None
            rck4.status = "available"
            db.commit()

        # Cancel any pending/assigned transport requests to CNC-01 test positions
        cnc01_locs = db.query(Location.id).filter(Location.machine_code == "CNC-01").all()
        cnc01_ids = [l[0] for l in cnc01_locs]
        db.query(TransportRequest).filter(
            TransportRequest.destination_location_id.in_(cnc01_ids),
            TransportRequest.status.in_(["pending", "assigned", "in_progress"]),
        ).update({"status": "cancelled"}, synchronize_session=False)
        db.commit()

        print("\n--- TEST 1: Nearest Cart Selection via 2D Euclidean Distance ---")
        cnc01_p1 = db.query(Location).filter(Location.location_code == "CNC01_POS1").first()
        m1 = db.query(Item).filter(Item.sku == "MDL-01").first()
        assert cnc01_p1 is not None, "CNC01_POS1 not found"
        assert m1 is not None, "MDL-01 not found"

        cart = DispatchService.find_nearest_available_cart(db, cnc01_p1, m1.id, 0)
        print(f"Nearest Level 0 cart for CNC01_POS1: {cart.cart_code if cart else 'None'}")
        assert cart is not None, "Expected to find an available Level 0 cart"

        print("\n--- TEST 2: Request Material to Empty CNC Position (CNC01_POS1) ---")
        result = DispatchService.request_material_for_station(
            db, destination_location_id=cnc01_p1.id, item_id=m1.id
        )
        print("Dispatch result:", result)
        assert result["success"] is True
        assert result["status"] == "assigned"
        assert cart.is_locked is True, "Cart should be locked"

        # Simulate AMR Arrival
        print("\n--- TEST 3: Simulate AMR Arrival at CNC01_POS1 ---")
        task = db.query(FleetTask).filter(FleetTask.task_code == result["fleet_task_code"]).first()
        assert task is not None, "Expected sent FleetTask"
        arrival_result = DispatchService.simulate_fleet_arrival(db, task.id)
        print("Arrival result:", arrival_result)
        assert arrival_result["success"] is True
        assert cart.location_id == cnc01_p1.id

        print("\n--- TEST 4: Double-Buffering / Pos 2 Calling (Zero CNC Starvation) ---")
        cnc01_p2 = db.query(Location).filter(Location.location_code == "CNC01_POS2").first()
        assert cnc01_p2 is not None, "CNC01_POS2 not found"
        # CNC01_POS2 calls material while POS1 is occupied!
        res_p2 = DispatchService.request_material_for_station(
            db, destination_location_id=cnc01_p2.id, item_id=m1.id
        )
        print("POS2 call result (Double-buffer):", res_p2)
        assert res_p2["success"] is True

        print("\n--- TEST 5: Report Stage 1 Completed at CNC01_POS1 ---")
        stage_comp = DispatchService.report_stage_completed(db, station_location_id=cnc01_p1.id)
        print("Stage completed result:", stage_comp)
        assert stage_comp["success"] is True
        assert stage_comp["action"] == "stage_completed"
        assert stage_comp["completed_level"] == 1
        assert cart.current_stage_level == 1

        rec = (
            db.query(ProductionRecord)
            .filter(ProductionRecord.cart_id == cart.id, ProductionRecord.stage_level == 1)
            .first()
        )
        assert rec is not None, "ProductionRecord must be created"
        print(f"Production record verified: Cart={rec.cart_code}, Level={rec.stage_level}, Machine={rec.machine_code}")

        print("\n--- TEST 6: Final Stage Completion (CNC-04) & Wash Transfer ---")
        cnc04_p1 = db.query(Location).filter(Location.location_code == "CNC04_POS1").first()
        cart_at_cnc4 = (
            db.query(ItemStock)
            .filter(ItemStock.location_id == cnc04_p1.id, ItemStock.is_active.is_(True))
            .first()
        )
        if cart_at_cnc4:
            wash_comp = DispatchService.report_stage_completed(db, station_location_id=cnc04_p1.id)
            print("Final CNC step wash transfer result:", wash_comp)
            assert wash_comp["success"] is True
            assert wash_comp["action"] in ["sent_to_wash", "queued_for_wash"]

        print("\n--- TEST 7: Release Wash Slot & Return Empty Cart ---")
        wash1 = db.query(Location).filter(Location.location_code == "WASH-01").first()
        rel_wash = DispatchService.release_wash_slot_and_return_empty(db, wash_location_id=wash1.id)
        print("Wash release result:", rel_wash)
        assert rel_wash["success"] is True

        print("\n==========================================")
        print("ALL 7 CORE DISPATCH ENGINE TESTS PASSED!")
        print("==========================================")

    except Exception as e:
        db.rollback()
        print(f"\nTEST FAILED WITH ERROR: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
