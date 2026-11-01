from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.auth.auth_model import User, Role, Permission, UserRole, UserWarehouse
from app.core.security import get_password_hash


def create_admin():
    db = SessionLocal()
    try:
        # 1. Ensure all 4 production roles exist
        roles_data = [
            ("admin", "Quản trị viên / Quản đốc xưởng"),
            ("operator_raw", "Operator Cấp Phôi (Khu Nguyên Liệu)"),
            ("operator_cnc", "Operator Vận Hành Máy CNC"),
            ("operator_washing", "Operator Khu Tẩy Rửa"),
        ]
        roles_by_name = {}
        for r_name, r_desc in roles_data:
            r = db.query(Role).filter(Role.name == r_name).first()
            if not r:
                r = Role(name=r_name, description=r_desc)
                db.add(r)
                db.flush()
                print(f"Created role: {r_name}")
            roles_by_name[r_name] = r

        admin_role = roles_by_name["admin"]

        # 2. Ensure Wildcard permission (*) for admin
        wildcard = db.query(Permission).filter(Permission.code == "*").first()
        if not wildcard:
            wildcard = Permission(code="*", name="All Permissions", module="all", description="Full system access")
            db.add(wildcard)
            db.flush()
            print("Created wildcard permission (*)")

        if wildcard not in admin_role.permissions:
            admin_role.permissions.append(wildcard)
            db.flush()

        # 3. Ensure admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_password = get_password_hash("admin123")
            admin_user = User(
                username="admin",
                email="admin@kuka.com",
                hashed_password=hashed_password,
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
            print("Admin user created! Username: admin, Password: admin123")
        else:
            admin_user.is_active = True
            print("Admin user already exists.")

        # 4. Assign admin role to admin user
        has_role = db.query(UserRole).filter(
            UserRole.user_id == admin_user.id,
            UserRole.role_id == admin_role.id,
        ).first()
        if not has_role:
            db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            print("Assigned admin role to admin user.")

        # 5. Link admin user to Warehouse if exists
        wh = db.query(Warehouse).first()
        if wh:
            has_wh = db.query(UserWarehouse).filter(
                UserWarehouse.user_id == admin_user.id,
                UserWarehouse.warehouse_id == wh.id,
            ).first()
            if not has_wh:
                db.add(UserWarehouse(user_id=admin_user.id, warehouse_id=wh.id))
                print(f"Linked admin user to Warehouse: {wh.code}")

        db.commit()
        print("[OK] Admin user and roles setup complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
