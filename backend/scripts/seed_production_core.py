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
from app.modules.warehouse.notificcation.notification_model import Notification  # noqa: F401
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

        # 2. Physical CNC Machines (3NF)
        machine_defs = [
            ("CNC-01", "Máy CNC 01 (Level 1)", 1),
            ("CNC-02", "Máy CNC 02 (Level 1)", 1),
            ("CNC-03", "Máy CNC 03 (Level 2)", 2),
            ("CNC-04", "Máy CNC 04 (Level 3)", 3),
        ]
        machines_by_code: dict[str, Machine] = {}
        for m_code, m_name, m_stage in machine_defs:
            m = db.query(Machine).filter(Machine.machine_code == m_code).first()
            if not m:
                m = Machine(
                    machine_code=m_code,
                    machine_name=m_name,
                    default_stage_level=m_stage,
                    warehouse_id=warehouse.id,
                    is_active=True,
                )
                db.add(m)
                db.flush()
            else:
                m.machine_name = m_name
                m.default_stage_level = m_stage
                m.warehouse_id = warehouse.id
                m.is_active = True
            machines_by_code[m_code] = m

        # 3. Locations
        location_defs = [
            # Raw Material Staging
            ("RAW-01", "Khu Nguyên Liệu 01", "RAW-01", "RAW_MATERIAL", None, None, None),
            ("RAW-02", "Khu Nguyên Liệu 02", "RAW-02", "RAW_MATERIAL", None, None, None),
            ("RAW-03", "Khu Nguyên Liệu 03", "RAW-03", "RAW_MATERIAL", None, None, None),
            # CNC Stage 1 (CNC-01 & CNC-02)
            ("CNC-01-POS1", "Máy CNC 01 - Vị trí 1 (Gia công)", "CNC-01-POS1", "CNC_SLOT", "CNC-01", 1, 1),
            ("CNC-01-POS2", "Máy CNC 01 - Vị trí 2 (Chờ)", "CNC-01-POS2", "CNC_SLOT", "CNC-01", 2, 1),
            ("CNC-02-POS1", "Máy CNC 02 - Vị trí 1 (Gia công)", "CNC-02-POS1", "CNC_SLOT", "CNC-02", 1, 1),
            ("CNC-02-POS2", "Máy CNC 02 - Vị trí 2 (Chờ)", "CNC-02-POS2", "CNC_SLOT", "CNC-02", 2, 1),
            # CNC Stage 2 (CNC-03)
            ("CNC-03-POS1", "Máy CNC 03 - Vị trí 1 (Gia công)", "CNC-03-POS1", "CNC_SLOT", "CNC-03", 1, 2),
            ("CNC-03-POS2", "Máy CNC 03 - Vị trí 2 (Chờ)", "CNC-03-POS2", "CNC_SLOT", "CNC-03", 2, 2),
            # CNC Stage 3 (CNC-04)
            ("CNC-04-POS1", "Máy CNC 04 - Vị trí 1 (Gia công)", "CNC-04-POS1", "CNC_SLOT", "CNC-04", 1, 3),
            ("CNC-04-POS2", "Máy CNC 04 - Vị trí 2 (Chờ)", "CNC-04-POS2", "CNC_SLOT", "CNC-04", 2, 3),
            # Washing Station
            ("WASH-01", "Trạm Tẩy Rửa 01", "WASH-01", "WASHING_SLOT", None, 1, None),
            # Empty Cart Buffer
            ("EMPTY-01", "Bãi Xe Rỗng 01", "EMPTY-01", "EMPTY_CART_BUFFER", None, 1, None),
            ("EMPTY-02", "Bãi Xe Rỗng 02", "EMPTY-02", "EMPTY_CART_BUFFER", None, 2, None),
        ]

        locations_by_code: dict[str, Location] = {}
        for code, name, bin_code, loc_type, machine_code, pos_idx, def_stage in location_defs:
            loc = (
                db.query(Location)
                .filter(
                    Location.warehouse_id == warehouse.id,
                    Location.location_code == code,
                )
                .first()
            )
            machine_obj = machines_by_code.get(machine_code) if machine_code else None
            if not loc:
                loc = Location(
                    location_code=code,
                    location_name=name,
                    bin_code=bin_code,
                    location_type=loc_type,
                    machine_id=machine_obj.id if machine_obj else None,
                    machine_code=machine_code,
                    position_index=pos_idx,
                    default_stage_level=def_stage,
                    warehouse_id=warehouse.id,
                    is_active=True,
                )
                db.add(loc)
                db.flush()
            else:
                loc.location_type = loc_type
                loc.machine_id = machine_obj.id if machine_obj else None
                loc.machine_code = machine_code
                loc.position_index = pos_idx
                loc.default_stage_level = def_stage
                loc.is_active = True
            locations_by_code[code] = loc

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
                    base_quantity=1,
                    standard_quantity_per_cart=std_qty,
                    max_quantity=10000,
                    min_quantity=100,
                    is_active=True,
                    warehouse_id=warehouse.id,
                    details={"type": "CNC_PART"},
                )
                db.add(item)
                db.flush()
            else:
                item.standard_quantity_per_cart = std_qty
            items_by_sku[sku] = item

        # 5. Production Routes & Normalized 3NF RouteStepMachine
        route_a = db.query(ProductionRoute).filter(ProductionRoute.route_code == "RT-MODEL-A-V1").first()
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
        for cart_code, sku, loc_code, qty, created_ts in cart_defs:
            cart = db.query(ItemStock).filter(ItemStock.cart_code == cart_code).first()
            if not cart:
                cart = ItemStock(
                    cart_code=cart_code,
                    item_id=items_by_sku[sku].id,
                    location_id=locations_by_code[loc_code].id,
                    quantity=qty,
                    current_stage_level=0,
                    is_locked=False,
                    locked_by_task_id=None,
                    destination_location_id=None,
                    status="available",
                    is_active=True,
                    created_at=created_ts,
                )
                db.add(cart)
            else:
                cart.item_id = items_by_sku[sku].id
                cart.location_id = locations_by_code[loc_code].id
                cart.quantity = qty
                cart.current_stage_level = 0
                cart.is_locked = False
                cart.locked_by_task_id = None
                cart.destination_location_id = None
                cart.status = "available"
                cart.is_active = True
                cart.created_at = created_ts

        db.commit()
        print("✅ Seed dữ liệu CNC Production & AMR Dispatch (3NF Machine) thành công!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_production_core()
