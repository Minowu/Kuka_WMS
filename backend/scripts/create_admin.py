from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.auth.auth_model import User, Role, UserRole
from app.core.security import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        # Check if role exists
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        # Check if user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_password = get_password_hash("admin123")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            # Assign role
            user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
            db.add(user_role)
            db.commit()
            print("Admin user created successfully! Username: admin, Password: admin123")
        else:
            print("Admin user already exists.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
