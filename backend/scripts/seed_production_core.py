"""
Seed script for Warehouse & Core Production Roles initialization.

Seeds:
1. 1 Factory Warehouse (WH-CNC) — Khung xưởng sản xuất cơ khí CNC tự động hóa AMR.
2. 4 Core Production Roles:
   - `admin`: Quản trị viên / Quản đốc xưởng
   - `operator_raw`: Operator Cấp Phôi (Khu Nguyên Liệu)
   - `operator_cnc`: Operator Vận Hành Máy CNC
   - `operator_washing`: Operator Khu Tẩy Rửa
3. Wildcard Permission (*) assigned to admin.
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.auth.auth_model import Role, Permission


def seed_production_core() -> None:
    db = SessionLocal()
    try:
        # 1. Warehouse (WH-CNC)
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
                print("Created new Warehouse WH-CNC.")
            else:
                print(f"Using existing Warehouse: {warehouse.code}")
        else:
            print(f"Warehouse WH-CNC already exists: {warehouse.code}")

        # 2. 4 Standard Production Roles
        roles_data = [
            ("admin", "Quản trị viên / Quản đốc xưởng"),
            ("operator_raw", "Operator Cấp Phôi (Khu Nguyên Liệu)"),
            ("operator_cnc", "Operator Vận Hành Máy CNC"),
            ("operator_washing", "Operator Khu Tẩy Rửa"),
        ]
        roles_by_name: dict[str, Role] = {}
        for r_name, r_desc in roles_data:
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name, description=r_desc)
                db.add(role)
                db.flush()
                print(f"Created Role: {r_name}")
            else:
                role.description = r_desc
            roles_by_name[r_name] = role

        # 3. Wildcard Permission (*) for Admin
        wildcard_perm = db.query(Permission).filter(Permission.code == "*").first()
        if not wildcard_perm:
            wildcard_perm = Permission(code="*", name="All Permissions", module="all", description="Full system access")
            db.add(wildcard_perm)
            db.flush()
            print("Created Wildcard Permission: *")

        admin_role = roles_by_name.get("admin")
        if admin_role and wildcard_perm not in admin_role.permissions:
            admin_role.permissions.append(wildcard_perm)
            print("Linked Wildcard Permission (*) to Admin role.")

        db.commit()
        print("[OK] Seed Warehouse (WH-CNC) & Core Production Roles successful!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_production_core()
