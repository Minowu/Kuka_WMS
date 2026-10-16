"""Seed script for KUKA AMR Production Core Engine.

Populates:
1. 7 Part Models (MDL-01 .. MDL-07) with standard_quantity_per_cart = 120
2. 8 CNC Locations (4 machines x 2 independent In/Out positions: CNC01_POS1, CNC01_POS2 .. CNC04_POS2)
3. 7 Raw Material Locations (VT-01 .. VT-07)
4. 4 Washing Slots (WASH-01 .. WASH-04)
5. 4 Empty Cart Buffer Slots (BUF-01 .. BUF-04)
6. Sample Production Routes & Steps for Models (Parallel machines & is_final_cnc_step)
7. 4 Workshop Users with user_locations permissions
8. Sample physical WIP Carts stationed across positions
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.modules.auth.auth_model import (
    User, UserRole, UserWarehouse, Role, RolePermission, Permission,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse, Zone
from app.modules.warehouse.location_map.location_model import Location, WarehouseMap
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.unit.unit_model import Unit, ItemUnit
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.notificcation.notification_model import Notification
from app.modules.warehouse.inbound_order.inbound_order_model import (
    InboundOrder, InboundOrderDetail, InboundOrderAllocation,
)
from app.modules.warehouse.outbound_order.outbound_order_model import (
    OutboundOrder, OutboundOrderDetail, OutboundOrderAllocation,
)
from app.modules.warehouse.stocktake.stocktake_model import Stocktake, StocktakeItemStock
from app.modules.warehouse.transaction_history.history_model import Transaction, History
from app.modules.warehouse.dashboard.dashboard_model import InventoryDailySnapshot
from app.modules.robot.robot_model import RobotTask, TaskStatus
from app.modules.production.production_models import (
    UserLocation,
    ProductionRoute,
    RouteStep,
    TransportRequest,
    TransportQueue,
    FleetTask,
    ProductionRecord,
)


def seed_production_core():
    db: Session = SessionLocal()
    try:
        print("=== 1. Checking Warehouse & Master Setup ===")
        wh = db.query(Warehouse).first()
        if not wh:
            wh = Warehouse(code="WH-MAIN", name="Xưởng Cơ Khí KUKA AMR")
            db.add(wh)
            db.commit()
            db.refresh(wh)
        print(f"Using Warehouse ID: {wh.id} ({wh.name})")

        unit_piece = db.query(Unit).filter(Unit.name == "Cai").first()
        if not unit_piece:
            unit_piece = db.query(Unit).first()
        if not unit_piece:
            unit_piece = Unit(name="Cai")
            db.add(unit_piece)
            db.commit()
            db.refresh(unit_piece)

        # Ensure operator role exists
        operator_role = db.query(Role).filter(Role.name == "operator").first()
        if not operator_role:
            operator_role = Role(name="operator", description="Công nhân vận hành phân xưởng")
            db.add(operator_role)
            db.commit()
            db.refresh(operator_role)

        print("=== 2. Seeding 7 Product Models (120 parts/cart) ===")
        models_data = [
            ("MDL-01", "Model 1: Trục Rotor", "Trục động cơ chính AMR", 120),
            ("MDL-02", "Model 2: Hộp Giảm Tốc", "Vỏ hộp số bánh răng hành tinh", 120),
            ("MDL-03", "Model 3: Mặt Bích Động Cơ", "Bích gá tiêu chuẩn KUKA", 120),
            ("MDL-04", "Model 4: Giá Đỡ Bánh Xe", "Khung gầm chịu tải 1500kg", 120),
            ("MDL-05", "Model 5: Khớp Cánh Tay 1", "Khớp xoay trục J1 hợp kim", 120),
            ("MDL-06", "Model 6: Khớp Cánh Tay 2", "Khớp nâng trục J2 chịu lực", 120),
            ("MDL-07", "Model 7: Bàn Nâng AMR", "Mặt bàn nâng thủy lực tích hợp", 120),
        ]

        items_map = {}
        for sku, name, desc, std_qty in models_data:
            item = db.query(Item).filter(Item.sku == sku).first()
            if not item:
                item = Item(
                    sku=sku,
                    name=name,
                    description=desc,
                    standard_quantity_per_cart=std_qty,
                    base_quantity=1,
                    base_unit_id=unit_piece.id,
                    warehouse_id=wh.id,
                    max_quantity=50000,
                    min_quantity=0,
                    supplier="KUKA Robotics Machining",
                    is_active=True,
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                print(f"  + Created Model: {sku} - {name} (std_qty={std_qty})")
            else:
                item.standard_quantity_per_cart = std_qty
                db.commit()
                print(f"  * Existing Model: {sku} - {name}")
            items_map[sku] = item

        print("=== 3. Seeding Locations ===")
        # 3.1. 7 Raw Material Locations
        raw_locations_data = [
            (f"VT-0{i}", f"Nguyên Liệu - Vị trí 0{i}", "RAW_MATERIAL", None, None, 500 + (i - 1) * 300, 500)
            for i in range(1, 8)
        ]
        # 3.2. 8 CNC Locations (4 machines x 2 positions)
        cnc_locations_data = [
            ("CNC01_POS1", "CNC-01 (Vị trí 1)", "CNC_SLOT", "CNC-01", 1, 2500, 1500),
            ("CNC01_POS2", "CNC-01 (Vị trí 2)", "CNC_SLOT", "CNC-01", 2, 2500, 2200),
            ("CNC02_POS1", "CNC-02 (Vị trí 1)", "CNC_SLOT", "CNC-02", 1, 4000, 1500),
            ("CNC02_POS2", "CNC-02 (Vị trí 2)", "CNC_SLOT", "CNC-02", 2, 4000, 2200),
            ("CNC03_POS1", "CNC-03 (Vị trí 1)", "CNC_SLOT", "CNC-03", 1, 5500, 1500),
            ("CNC03_POS2", "CNC-03 (Vị trí 2)", "CNC_SLOT", "CNC-03", 2, 5500, 2200),
            ("CNC04_POS1", "CNC-04 (Vị trí 1)", "CNC_SLOT", "CNC-04", 1, 7000, 1500),
            ("CNC04_POS2", "CNC-04 (Vị trí 2)", "CNC_SLOT", "CNC-04", 2, 7000, 2200),
        ]
        # 3.3. 4 Washing Slots
        washing_locations_data = [
            (f"WASH-0{i}", f"Khu Rửa - Slot 0{i}", "WASHING_SLOT", None, i, 8800, 1200 + (i - 1) * 600)
            for i in range(1, 5)
        ]
        # 3.4. 4 Empty Cart Buffer Slots
        buffer_locations_data = [
            (f"BUF-0{i}", f"Bãi Đệm Xe Rỗng 0{i}", "EMPTY_CART_BUFFER", None, i, 1000, 3200 + (i - 1) * 600)
            for i in range(1, 5)
        ]

        all_locs = raw_locations_data + cnc_locations_data + washing_locations_data + buffer_locations_data
        locations_map = {}
        for code, name, loc_type, machine, pos_idx, mx, my in all_locs:
            loc = (
                db.query(Location)
                .filter(Location.warehouse_id == wh.id, Location.location_code == code)
                .first()
            )
            if not loc:
                loc = Location(
                    warehouse_id=wh.id,
                    location_code=code,
                    location_name=name,
                    location_type=loc_type,
                    machine_code=machine,
                    position_index=pos_idx,
                    map_x=mx,
                    map_y=my,
                    is_active=True,
                )
                db.add(loc)
                db.commit()
                db.refresh(loc)
                print(f"  + Created Location: {code} ({name}) type={loc_type}")
            else:
                loc.location_name = name
                loc.location_type = loc_type
                loc.machine_code = machine
                loc.position_index = pos_idx
                loc.map_x = mx
                loc.map_y = my
                db.commit()
                print(f"  * Updated Location: {code} ({name}) type={loc_type}")
            locations_map[code] = loc

        print("=== 4. Seeding Production Routes & Steps ===")
        # Route for Model 1
        m1 = items_map["MDL-01"]
        route1 = db.query(ProductionRoute).filter(ProductionRoute.route_code == "ROUTE-MDL01-STD").first()
        if not route1:
            route1 = ProductionRoute(
                route_code="ROUTE-MDL01-STD",
                route_name="Quy trình gia công Chuẩn - Model 1 (Trục Rotor)",
                item_id=m1.id,
                version=1,
                is_active=True,
            )
            db.add(route1)
            db.commit()
            db.refresh(route1)

            # Step 1: Phay Thô (CNC-01 or CNC-02 parallel)
            step1 = RouteStep(
                route_id=route1.id,
                step_number=1,
                stage_level=1,
                step_name="Phay Thô",
                allowed_machines=["CNC-01", "CNC-02"],
                is_final_cnc_step=False,
            )
            # Step 2: Phay Tinh (CNC-03)
            step2 = RouteStep(
                route_id=route1.id,
                step_number=2,
                stage_level=2,
                step_name="Phay Tinh",
                allowed_machines=["CNC-03"],
                is_final_cnc_step=False,
            )
            # Step 3: Khoan Tappi & Hoàn Tất (CNC-04) -> FINAL CNC STEP
            step3 = RouteStep(
                route_id=route1.id,
                step_number=3,
                stage_level=3,
                step_name="Khoan Tappi & Hoàn Tất CNC",
                allowed_machines=["CNC-04"],
                is_final_cnc_step=True,
            )
            db.add_all([step1, step2, step3])
            db.commit()
            print("  + Created Route and 3 Steps for MDL-01")
        else:
            print("  * Existing Route for MDL-01")

        # Route for Model 2
        m2 = items_map["MDL-02"]
        route2 = db.query(ProductionRoute).filter(ProductionRoute.route_code == "ROUTE-MDL02-STD").first()
        if not route2:
            route2 = ProductionRoute(
                route_code="ROUTE-MDL02-STD",
                route_name="Quy trình gia công Chuẩn - Model 2 (Hộp Giảm Tốc)",
                item_id=m2.id,
                version=1,
                is_active=True,
            )
            db.add(route2)
            db.commit()
            db.refresh(route2)

            step1 = RouteStep(
                route_id=route2.id,
                step_number=1,
                stage_level=1,
                step_name="Phay Thô Thân Hộp",
                allowed_machines=["CNC-01", "CNC-02"],
                is_final_cnc_step=False,
            )
            step2 = RouteStep(
                route_id=route2.id,
                step_number=2,
                stage_level=2,
                step_name="Doa Lỗ Vòng Bi",
                allowed_machines=["CNC-03"],
                is_final_cnc_step=False,
            )
            step3 = RouteStep(
                route_id=route2.id,
                step_number=3,
                stage_level=3,
                step_name="Gia Công Mặt Ghép Bích",
                allowed_machines=["CNC-04"],
                is_final_cnc_step=True,
            )
            db.add_all([step1, step2, step3])
            db.commit()
            print("  + Created Route and 3 Steps for MDL-02")

        print("=== 5. Seeding 4 Workshop Users & user_locations ===")
        users_config = [
            (
                "pda_nguyenlieu",
                "nguyenlieu@kuka.com",
                "pda123",
                "Công nhân Cấp Phôi Nguyên Liệu",
                [f"VT-0{i}" for i in range(1, 8)],
            ),
            (
                "pda_cnc_stage1",
                "cnc_stage1@kuka.com",
                "pda123",
                "Công nhân CNC Stage 1 (CNC-01 & CNC-02)",
                ["CNC01_POS1", "CNC01_POS2", "CNC02_POS1", "CNC02_POS2"],
            ),
            (
                "pda_cnc_stage23",
                "cnc_stage23@kuka.com",
                "pda123",
                "Công nhân CNC Stage 2 & 3 (CNC-03 & CNC-04)",
                ["CNC03_POS1", "CNC03_POS2", "CNC04_POS1", "CNC04_POS2"],
            ),
            (
                "pda_tayrua",
                "tayrua@kuka.com",
                "pda123",
                "Công nhân Khu Tẩy Rửa",
                [f"WASH-0{i}" for i in range(1, 5)],
            ),
        ]

        for username, email, pwd, note, assigned_loc_codes in users_config:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                user_role = UserRole(user_id=user.id, role_id=operator_role.id)
                db.add(user_role)
                db.commit()
                print(f"  + Created User: {username} ({note})")
            else:
                print(f"  * Existing User: {username}")

            # Assign user_locations
            for loc_code in assigned_loc_codes:
                loc = locations_map.get(loc_code)
                if loc:
                    ul = (
                        db.query(UserLocation)
                        .filter(UserLocation.user_id == user.id, UserLocation.location_id == loc.id)
                        .first()
                    )
                    if not ul:
                        ul = UserLocation(user_id=user.id, location_id=loc.id)
                        db.add(ul)
            db.commit()
            print(f"    -> Assigned {len(assigned_loc_codes)} locations to {username}")

        print("=== 6. Seeding Initial Physical WIP Carts ===")
        sample_carts = [
            ("RCK-VT01-1021", "MDL-01", "VT-01", 120, 0, False),
            ("RCK-VT02-4412", "MDL-02", "VT-02", 120, 0, False),
            ("RCK-VT04-7729", "MDL-03", "VT-04", 120, 0, False),
            ("RCK-CNC02-2101", "MDL-01", "CNC02_POS1", 120, 1, False),
            ("RCK-CNC03-3101", "MDL-01", "CNC03_POS1", 120, 2, False),
            ("RCK-CNC04-4101", "MDL-01", "CNC04_POS1", 120, 3, False),
            ("RCK-WASH-1101", "MDL-01", "WASH-01", 120, 3, False),
            ("RCK-BUF01-0001", "MDL-01", "BUF-01", 0, 0, False),
            ("RCK-BUF02-0002", "MDL-02", "BUF-02", 0, 0, False),
        ]

        for cart_code, sku, loc_code, qty, stage_lvl, locked in sample_carts:
            cart = db.query(ItemStock).filter(ItemStock.cart_code == cart_code).first()
            loc = locations_map.get(loc_code)
            item = items_map.get(sku)
            if not cart and loc and item:
                cart = ItemStock(
                    cart_code=cart_code,
                    item_id=item.id,
                    location_id=loc.id,
                    quantity=qty,
                    current_stage_level=stage_lvl,
                    is_locked=locked,
                    status="available" if not locked else "locked",
                    unit_id=unit_piece.id,
                    is_active=True,
                )
                db.add(cart)
                db.commit()
                print(f"  + Created Cart: {cart_code} ({sku}) at {loc_code} Level={stage_lvl}")
            elif cart:
                print(f"  * Existing Cart: {cart_code}")

        print("\nSUCCESS: All KUKA AMR Core Production data seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"\nERROR seeding production core data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_production_core()
