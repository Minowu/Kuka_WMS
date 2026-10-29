"""Unit test to verify CartSelector never dispatches a cart between positions of the same machine."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.auth.auth_model import User  # ORM registry
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.production_models import FleetTask, Machine, TransportRequest  # ORM registry
from app.modules.warehouse.item.item_model import Item  # ORM registry
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse  # ORM registry


class TestCartSelectorSameMachine(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.selector = CartSelector()
        self.created_ids = {
            "stocks": [],
            "locations": [],
            "machines": [],
        }
        wh = self.db.query(Warehouse).first()
        self.warehouse_id = wh.id if wh else 1
        it = self.db.query(Item).first()
        self.item_id = it.id if it else 1

    def tearDown(self):
        try:
            if self.created_ids["stocks"]:
                self.db.query(ItemStock).filter(ItemStock.id.in_(self.created_ids["stocks"])).delete(synchronize_session=False)
            if self.created_ids["locations"]:
                self.db.query(Location).filter(Location.id.in_(self.created_ids["locations"])).delete(synchronize_session=False)
            if self.created_ids["machines"]:
                self.db.query(Machine).filter(Machine.id.in_(self.created_ids["machines"])).delete(synchronize_session=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_cart_selector_excludes_same_machine_slots(self):
        """
        Verify that if Machine M has Slot POS1 and Slot POS2:
        A cart sitting at POS1 must NOT be selected when material is requested for POS2!
        """
        # 1. Create a test Machine M
        m1 = Machine(
            machine_name="TEST-CNC-SAME-M",
            machine_code="M_TEST_SAME_M",
        )
        self.db.add(m1)
        self.db.flush()
        self.created_ids["machines"].append(m1.id)

        # 2. Create 2 slots for Machine M: pos1 and pos2 (very close coordinates)
        loc_pos1 = Location(
            location_code="TEST-POS1-M1",
            location_name="Machine 1 Slot 1",
            location_type="CNC_SLOT",
            machine_id=m1.id,
            warehouse_id=self.warehouse_id,
            position_index=1,
            map_x=10.0,
            map_y=10.0,
            is_active=True,
        )
        loc_pos2 = Location(
            location_code="TEST-POS2-M1",
            location_name="Machine 1 Slot 2",
            location_type="CNC_SLOT",
            machine_id=m1.id,
            warehouse_id=self.warehouse_id,
            position_index=2,
            map_x=10.5,
            map_y=10.0,
            is_active=True,
        )
        self.db.add_all([loc_pos1, loc_pos2])
        self.db.flush()
        self.created_ids["locations"].extend([loc_pos1.id, loc_pos2.id])

        # 3. Create a cart at POS1 with stage_level = 1, item_id = self.item_id
        cart_pos1 = ItemStock(
            item_id=self.item_id,
            container_code="CART-TEST-POS1",
            location_id=loc_pos1.id,
            current_stage_level=1,
            status="occupied",
            is_locked=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(cart_pos1)
        self.db.commit()
        self.created_ids["stocks"].append(cart_pos1.id)

        # Test Case 1: Calling material for POS2 (on same Machine M)
        # Should return None because the only available cart is at POS1 on the SAME machine!
        found_cart = self.selector.find_fifo_available_cart(
            db=self.db,
            item_id=self.item_id,
            stage_level=1,
            target_location=loc_pos2,
        )
        self.assertIsNone(
            found_cart,
            "CartSelector must NOT pick a cart sitting at POS1 of the SAME machine for POS2!",
        )

        # Test Case 2: Now add another cart on a DIFFERENT machine (Machine M2) further away
        m2 = Machine(
            machine_name="TEST-CNC-OTHER",
            machine_code="M_TEST_OTHER",
        )
        self.db.add(m2)
        self.db.flush()
        self.created_ids["machines"].append(m2.id)

        loc_m2 = Location(
            location_code="TEST-POS1-M2",
            location_name="Machine 2 Slot 1",
            location_type="CNC_SLOT",
            machine_id=m2.id,
            warehouse_id=self.warehouse_id,
            position_index=1,
            map_x=50.0,
            map_y=50.0,
            is_active=True,
        )
        self.db.add(loc_m2)
        self.db.flush()
        self.created_ids["locations"].append(loc_m2.id)

        cart_m2 = ItemStock(
            item_id=self.item_id,
            container_code="CART-TEST-M2",
            location_id=loc_m2.id,
            current_stage_level=1,
            status="occupied",
            is_locked=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(cart_m2)
        self.db.commit()
        self.created_ids["stocks"].append(cart_m2.id)

        # Calling material for POS2 must now pick CART-TEST-M2 (from Machine 2), NOT CART-TEST-POS1
        found_cart = self.selector.find_fifo_available_cart(
            db=self.db,
            item_id=self.item_id,
            stage_level=1,
            target_location=loc_pos2,
        )
        self.assertIsNotNone(found_cart)
        self.assertEqual(
            found_cart.id,
            cart_m2.id,
            "CartSelector should pick the cart from Machine 2, completely ignoring the cart on the same machine!",
        )

        # Test Case 3: Target location itself has a cart
        found_cart_self = self.selector.find_fifo_available_cart(
            db=self.db,
            item_id=self.item_id,
            stage_level=1,
            target_location=loc_m2,
        )
        if found_cart_self:
            self.assertNotEqual(
                found_cart_self.id,
                cart_m2.id,
                "CartSelector must never pick a cart sitting at target_location itself!",
            )

    def test_raw_material_cart_exclusion_at_target_location(self):
        """Verify CartSelector also excludes carts sitting at target_location for raw material (stage_level = 0)."""
        loc_raw = Location(
            location_code="TEST-RAW-LOC",
            location_name="Raw Material Slot",
            location_type="RAW_MATERIAL",
            warehouse_id=self.warehouse_id,
            position_index=1,
            map_x=5.0,
            map_y=5.0,
            is_active=True,
        )
        self.db.add(loc_raw)
        self.db.flush()
        self.created_ids["locations"].append(loc_raw.id)

        cart_raw = ItemStock(
            item_id=self.item_id,
            container_code="CART-TEST-RAW",
            location_id=loc_raw.id,
            current_stage_level=0,
            status="occupied",
            is_locked=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(cart_raw)
        self.db.commit()
        self.created_ids["stocks"].append(cart_raw.id)

        # Target location is loc_raw itself -> must NOT pick cart_raw
        found = self.selector.find_fifo_available_cart(
            db=self.db,
            item_id=self.item_id,
            stage_level=0,
            target_location=loc_raw,
        )
        self.assertIsNone(found, "CartSelector must never pick a raw material cart sitting at target_location!")


if __name__ == "__main__":
    unittest.main()
