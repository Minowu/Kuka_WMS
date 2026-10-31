"""
Seed script for Warehouse / Production initialization.

Seeds:
1. 1 Factory Warehouse (WH-CNC) — Khung xuong san xuat co khi CNC tu dong hoa AMR.
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
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
                print("Created new Warehouse WH-CNC.")
            else:
                print(f"Using existing Warehouse: {warehouse.code}")
        else:
            print(f"Warehouse WH-CNC already exists: {warehouse.code}")

        db.commit()
        print("[OK] Seed Warehouse (WH-CNC) successful!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_production_core()
