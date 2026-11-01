"""
Script to wipe all operational mock data, leaving only user accounts,
real products, and unassigned map nodes for fresh setup.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main
from app.core.database import SessionLocal
from app.modules.production.production_models import (
    FleetApiCall,
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TaskStatus,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.item.item_model import Item


def reset_clean_slate():
    db = SessionLocal()
    try:
        print("Bắt đầu dọn dẹp toàn bộ dữ liệu vận hành mock...")

        # 1. Xóa các tác vụ vận hành, lịch sử, logs
        db.query(TaskStatus).delete()
        db.query(FleetApiCall).delete()
        db.query(FleetTask).delete()
        db.query(TransportQueue).delete()
        db.query(TransportRequest).delete()
        db.query(ProductionRecord).delete()
        db.query(ItemStock).delete()

        # 2. Xóa phân quyền vị trí user
        db.query(UserLocation).delete()

        # 3. Xóa các cấu hình Route và Máy CNC cũ
        db.query(RouteStepMachine).delete()
        db.query(RouteStep).delete()
        db.query(ProductionRoute).delete()

        # 4. Reset toàn bộ vị trí Map về UNASSIGNED
        for loc in db.query(Location).all():
            loc.location_type = "UNASSIGNED"
            loc.location_name = loc.location_label or str(loc.id)
            loc.machine_id = None
            loc.position_index = None
            loc.is_active = True
        db.flush()

        db.query(Machine).delete()

        # 5. Xóa các item mẫu (MODEL-A, MODEL-B), giữ lại sản phẩm của người dùng
        db.query(Item).filter(Item.sku.in_(["MODEL-A", "MODEL-B"])).delete()

        db.commit()
        print("✅ Đã dọn sạch 100% dữ liệu về trạng thái TRẮNG hoàn toàn!")
        print("   - Giữ nguyên: Tài khoản Users (admin, operators)")
        print("   - Giữ nguyên: Các Model sản phẩm do bạn tự tạo")
        print("   - Giữ nguyên: Các Node tọa độ bản đồ xưởng")
        print("   - Đã xóa sạch: Xe phôi, máy CNC, quy trình route, nhiệm vụ điều phối")
    finally:
        db.close()


if __name__ == "__main__":
    reset_clean_slate()
