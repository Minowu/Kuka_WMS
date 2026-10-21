"""
Seed script for CNC Production & KUKA AMR Dispatch Core (3NF Normalized).

Seeds:
1. 1 Factory Warehouse (WH-CNC) — no Zone table required.
2. 4 Physical CNC Machines in `machine` (`CNC-01`, `CNC-02`, `CNC-03`, `CNC-04`).
3. 14 Locations across 4 functional areas:
   - 3 Raw Material slots (RAW-01, RAW-02, RAW-03)
   - 8 CNC slots across 4 CNC machines (CNC-01..CNC-04, each with POS1 & POS2 linked via `machine_id`)
   - 1 Washing station (WASH-01)
   - 2 Empty Cart Buffer slots (EMPTY-01, EMPTY-02)
4. 2 Product Models (`Item`):
   - `MODEL-A` (120 pcs/cart, 3-stage CNC route: Level 1 -> Level 2 -> Level 3 -> Washing)
   - `MODEL-B` (80 pcs/cart, 2-stage CNC route: Level 1 -> Level 2 -> Washing)
5. Production Routes (`ProductionRoute`, `RouteStep`, and 3NF `RouteStepMachine`) for `MODEL-A` and `MODEL-B`.
6. 3 Initial Raw Material Carts (`ItemStock`: `CART-001`, `CART-002`, `CART-003`) at RAW-01..RAW-03.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.auth.auth_model import (  # noqa: F401
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserWarehouse,
)
from app.modules.production.production_models import (
    FleetTask,  # noqa: F401
    Machine,
    ProductionRecord,  # noqa: F401
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TaskStatus,  # noqa: F401
    TransportQueue,  # noqa: F401
    TransportRequest,  # noqa: F401
    UserLocation,  # noqa: F401
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


def seed_production_core() -> None:
    db = SessionLocal()
    try:
        # 1. Warehouse
        warehouse = db.query(Warehouse).filter(Warehouse.code == "WH-CNC").first()
        if not warehouse:
            warehouse = db.query(Warehouse).first()
            if not warehouse:
                warehouse = Warehouse(
                    code="WH-CNC",
                    name="Xưởng Gia Công CNC KUKA",
                    description="Xưởng sản xuất cơ khí CNC tự động hóa AMR",
                )
                db.add(warehouse)
                db.flush()

        # 2. Physical CNC Machines (3NF) - No default_stage_level
        machine_defs = [
            ("CNC-01", "Máy CNC 01"),
            ("CNC-02", "Máy CNC 02"),
            ("CNC-03", "Máy CNC 03"),
            ("CNC-04", "Máy CNC 04"),
        ]
        machines_by_code: dict[str, Machine] = {}
        for m_code, m_name in machine_defs:
            m = db.query(Machine).filter(Machine.machine_code == m_code).first()
            if not m:
                m = Machine(
                    machine_code=m_code,
                    machine_name=m_name,
                    warehouse_id=warehouse.id,
                )
                db.add(m)
                db.flush()
            else:
                m.machine_name = m_name
                m.warehouse_id = warehouse.id
            machines_by_code[m_code] = m

        # 3. Locations mapped strictly to the 16 real Rack nodes (functionType == 2) from map_CNC001_CNC001_28s.json
        # Format: (code, name, bin_code, loc_type, machine_code, pos_idx, node_label, map_x, map_y)
        location_defs = [
            # Raw Material Staging (7 slots) - VT-01..07 mapped to rack nodes
            ("VT-01", "Ô Cấp Phôi 1", "VT-01", "RAW_MATERIAL", None, 1, "51", 180913, 77500),
            ("VT-02", "Ô Cấp Phôi 2", "VT-02", "RAW_MATERIAL", None, 2, "50", 179713, 77500),
            ("VT-03", "Ô Cấp Phôi 3", "VT-03", "RAW_MATERIAL", None, 3, "4", 178513, 77500),
            ("VT-04", "Ô Cấp Phôi 4", "VT-04", "RAW_MATERIAL", None, 4, "17", 179713, 83800),
            ("VT-05", "Ô Cấp Phôi 5", "VT-05", "RAW_MATERIAL", None, 5, "18", 178513, 83800),
            ("VT-06", "Ô Cấp Phôi 6", "VT-06", "RAW_MATERIAL", None, 6, "20", 180913, 83800),
            ("VT-07", "Ô Cấp Phôi 7", "VT-07", "RAW_MATERIAL", None, 7, "23", 182113, 83800),

            # CNC Machines (CNC-01 with 2 slots POS1 & POS2; CNC-02..04 with POS1)
            ("CNC-01-POS1", "Máy CNC 01 - Vị trí 1", "CNC-01-POS1", "CNC_SLOT", "CNC-01", 1, "216", 164249, 52600),
            ("CNC-01-POS2", "Máy CNC 01 - Vị trí 2", "CNC-01-POS2", "CNC_SLOT", "CNC-01", 2, "249", 156049, 52600),
            ("CNC-02-POS1", "Máy CNC 02 - Vị trí 1", "CNC-02-POS1", "CNC_SLOT", "CNC-02", 1, "127", 171000, 41700),
            ("CNC-03-POS1", "Máy CNC 03 - Vị trí 1", "CNC-03-POS1", "CNC_SLOT", "CNC-03", 1, "128", 172500, 41700),
            ("CNC-04-POS1", "Máy CNC 04 - Vị trí 1", "CNC-04-POS1", "CNC_SLOT", "CNC-04", 1, "129", 174000, 41700),

            # Washing Station (2 slots)
            ("WASH-01", "Slot Rửa 1", "WASH-01", "WASHING_SLOT", None, 1, "130", 175500, 41700),
            ("WASH-02", "Slot Rửa 2", "WASH-02", "WASHING_SLOT", None, 2, "24", 183313, 83800),

            # Empty Cart Buffers (2 slots)
            ("EMPTY-01", "Bãi đệm 1", "EMPTY-01", "EMPTY_CART_BUFFER", None, 1, "25", 184513, 83800),
            ("EMPTY-02", "Bãi đệm 2", "EMPTY-02", "EMPTY_CART_BUFFER", None, 2, "26", 185713, 83800),
        ]

        # Locations are managed solely by user/map import. No auto-inserting of mock locations.
        locations_by_code: dict[str, Location] = {}
        for loc in db.query(Location).filter(Location.warehouse_id == warehouse.id).all():
            if loc.location_code:
                locations_by_code[loc.location_code] = loc
            if loc.location_label:
                locations_by_code[loc.location_label] = loc
            loc_code = loc.location_code or ""
            if loc_code.startswith("VT-"):
                pos_idx = loc.position_index or 1
                locations_by_code[f"RAW-0{pos_idx}"] = loc

        # 4. Product Models (Items)
        item_defs = [
            ("MODEL-A", "Phôi Trục Chính CNC Model A", 120),
            ("MODEL-B", "Phôi Mặt Bích CNC Model B", 80),
        ]
        items_by_sku: dict[str, Item] = {}
        for sku, name, std_qty in item_defs:
            item = db.query(Item).filter(Item.sku == sku).first()
            if not item:
                item = Item(
                    sku=sku,
                    name=name,
                    description=f"Sản phẩm cơ khí {name}",
                    supplier="KUKA_CNC",
                    standard_quantity_per_cart=std_qty,
                    warehouse_id=warehouse.id,
                    details={"type": "CNC_PART"},
                )
                db.add(item)
                db.flush()
            else:
                item.standard_quantity_per_cart = std_qty
            items_by_sku[sku] = item

        # 5. Production Routes & Normalized 3NF RouteStepMachine
        route_a = db.query(ProductionRoute).filter(ProductionRoute.item_id == items_by_sku["MODEL-A"].id, ProductionRoute.is_active.is_(True)).first()
        if not route_a:
            route_a = ProductionRoute(
                route_code="RT-MODEL-A-V1",
                route_name="Quy trình gia công 3 bước Model A",
                item_id=items_by_sku["MODEL-A"].id,
                version=1,
                is_active=True,
            )
            db.add(route_a)
            db.flush()

            steps_a = [
                (1, 1, "Gia công thô Level 1", ["CNC-01", "CNC-02"], False),
                (2, 2, "Gia công bán tinh Level 2", ["CNC-03"], False),
                (3, 3, "Gia công tinh Level 3", ["CNC-04"], True),
            ]
            for s_num, s_lvl, s_name, m_codes, is_final in steps_a:
                step = RouteStep(
                    route_id=route_a.id,
                    step_number=s_num,
                    stage_level=s_lvl,
                    step_name=s_name,
                    is_final_cnc_step=is_final,
                )
                db.add(step)
                db.flush()
                for mc in m_codes:
                    db.add(
                        RouteStepMachine(
                            route_step_id=step.id,
                            machine_id=machines_by_code[mc].id,
                        )
                    )

        route_b = db.query(ProductionRoute).filter(ProductionRoute.route_code == "RT-MODEL-B-V1").first()
        if not route_b:
            route_b = ProductionRoute(
                route_code="RT-MODEL-B-V1",
                route_name="Quy trình gia công 2 bước Model B",
                item_id=items_by_sku["MODEL-B"].id,
                version=1,
                is_active=True,
            )
            db.add(route_b)
            db.flush()

            steps_b = [
                (1, 1, "Tiện mặt đầu Level 1", ["CNC-01", "CNC-02"], False),
                (2, 2, "Khoan tâm Level 2", ["CNC-03"], True),
            ]
            for s_num, s_lvl, s_name, m_codes, is_final in steps_b:
                step = RouteStep(
                    route_id=route_b.id,
                    step_number=s_num,
                    stage_level=s_lvl,
                    step_name=s_name,
                    is_final_cnc_step=is_final,
                )
                db.add(step)
                db.flush()
                for mc in m_codes:
                    db.add(
                        RouteStepMachine(
                            route_step_id=step.id,
                            machine_id=machines_by_code[mc].id,
                        )
                    )

        # 6. Initial Raw Material Carts (FIFO timestamps staggered by 10 minutes)
        base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        cart_defs = [
            ("CART-001", "MODEL-A", "RAW-01", 120, base_time),
            ("CART-002", "MODEL-A", "RAW-02", 120, base_time + timedelta(minutes=10)),
            ("CART-003", "MODEL-B", "RAW-03", 80, base_time + timedelta(minutes=20)),
        ]
        occupied_loc_ids = {
            s.location_id for s in db.query(ItemStock.location_id).filter(ItemStock.is_active.is_(True)).all()
        }
        raw_candidates = db.query(Location).filter(
            Location.warehouse_id == warehouse.id,
            Location.location_type == "RAW_MATERIAL",
            Location.is_active.is_(True)
        ).all()

        for idx, (cart_code, sku, loc_code, qty, created_ts) in enumerate(cart_defs):
            target_loc = locations_by_code.get(loc_code)
            if not target_loc or target_loc.id in occupied_loc_ids:
                avail = [l for l in raw_candidates if l.id not in occupied_loc_ids]
                if not avail:
                    continue
                target_loc = avail[0]

            occupied_loc_ids.add(target_loc.id)

            cart = db.query(ItemStock).filter(ItemStock.cart_code == cart_code).first()
            if not cart:
                cart = ItemStock(
                    cart_code=cart_code,
                    item_id=items_by_sku[sku].id,
                    location_id=target_loc.id,
                    quantity=qty,
                    current_stage_level=0,
                    is_locked=False,
                    locked_by_task_id=None,
                    destination_location_id=None,
                    status="available",
                    created_at=created_ts,
                )
                db.add(cart)
            else:
                cart.item_id = items_by_sku[sku].id
                cart.location_id = target_loc.id
                cart.quantity = qty
                cart.current_stage_level = 0
                cart.is_locked = False
                cart.locked_by_task_id = None
                cart.destination_location_id = None
                cart.status = "available"
                cart.is_active = True
                cart.created_at = created_ts

        # 7. Production Users & Functional Station Permissions (Real Data)
        from app.core.security import get_password_hash

        role_admin = db.query(Role).filter(Role.name == "admin").first()
        if not role_admin:
            role_admin = Role(name="admin", description="Quản trị viên xưởng")
            db.add(role_admin)
            db.flush()

        role_operator = db.query(Role).filter(Role.name == "operator").first()
        if not role_operator:
            role_operator = Role(name="operator", description="Công nhân vận hành trạm")
            db.add(role_operator)
            db.flush()

        user_configs = [
            (
                "admin",
                "admin@kuka.com",
                "admin123",
                role_admin,
                [],  # admin has universal access to all stations
            ),
            (
                "op_raw",
                "op_raw@kuka.com",
                "123456",
                role_operator,
                ["VT-01", "VT-02", "VT-03", "VT-04", "VT-05", "VT-06", "VT-07"],
            ),
            (
                "op_cnc_stage1",
                "op_cnc_stage1@kuka.com",
                "123456",
                role_operator,
                ["CNC-01-POS1", "CNC-01-POS2", "CNC-02-POS1"],
            ),
            (
                "op_cnc_stage2",
                "op_cnc_stage2@kuka.com",
                "123456",
                role_operator,
                ["CNC-03-POS1", "CNC-04-POS1"],
            ),
            (
                "op_washing",
                "op_washing@kuka.com",
                "123456",
                role_operator,
                ["WASH-01", "WASH-02"],
            ),
        ]

        for uname, uemail, upwd, urole, loc_codes in user_configs:
            u = db.query(User).filter(User.username == uname).first()
            if not u:
                u = User(
                    username=uname,
                    email=uemail,
                    hashed_password=get_password_hash(upwd),
                )
                db.add(u)
                db.flush()
            else:
                u.email = uemail
                u.hashed_password = get_password_hash(upwd)
                u.is_active = True
                db.flush()

            # Ensure warehouse link
            uw = db.query(UserWarehouse).filter(
                UserWarehouse.user_id == u.id,
                UserWarehouse.warehouse_id == warehouse.id,
            ).first()
            if not uw:
                db.add(UserWarehouse(user_id=u.id, warehouse_id=warehouse.id))

            # Ensure role link
            db.query(UserRole).filter(UserRole.user_id == u.id).delete(synchronize_session=False)
            db.add(UserRole(user_id=u.id, role_id=urole.id))

            # Assign physical station locations
            db.query(UserLocation).filter(UserLocation.user_id == u.id).delete(synchronize_session=False)
            for lc in loc_codes:
                loc_obj = locations_by_code.get(lc)
                if loc_obj:
                    db.add(UserLocation(user_id=u.id, location_id=loc_obj.id))

        db.commit()
        print("✅ Seed dữ liệu CNC Production & AMR Dispatch (3NF Machine + 5 Users) thành công!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_production_core()

