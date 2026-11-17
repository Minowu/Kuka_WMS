"""Auto-split from dispatch_core — keep behavior identical."""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.logger import bind_context, get_logger, log_context
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")


def assign_locations_to_user(
    core,
    db: Session,
    user_id: int,
    location_ids: list[int],
) -> list[UserLocation]:
    """Assign stations/locations to an operator enforcing 1 user = 1 area."""
    unique_loc_ids = list(dict.fromkeys(location_ids))

    if unique_loc_ids:
        loc_objs = (
            db.query(Location)
            .filter(Location.id.in_(unique_loc_ids), Location.is_active.is_(True))
            .all()
        )
        if len(loc_objs) != len(unique_loc_ids):
            raise ValueError("Một hoặc nhiều vị trí (Location) không tồn tại hoặc đã bị khóa.")

        area_types = {loc.location_type for loc in loc_objs}
        if len(area_types) > 1:
            raise ValueError("Một tài khoản công nhân chỉ có thể được phân quyền trong 1 khu vực duy nhất.")

    db.query(UserLocation).filter(UserLocation.user_id == user_id).delete(synchronize_session=False)

    records = [
        UserLocation(user_id=user_id, location_id=loc_id)
        for loc_id in unique_loc_ids
    ]
    db.add_all(records)
    db.commit()
    return records
