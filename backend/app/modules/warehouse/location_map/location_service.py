"""Location service facade — thin re-exports (backward compatible)."""

from app.modules.warehouse.location_map.service.common import (
    location_ids_with_assigned_qr,
    move_assigned_stock_cache,
    overlay_status_with_assign_cache,
)
from app.modules.warehouse.location_map.service.crud import (
    delete_location,
    get_location_by_id,
    get_location_detail,
    get_locations_by_logic,
    list_locations,
    update_location,
    upsert_location,
)
from app.modules.warehouse.location_map.service.location_qr import (
    generate_qr_location_code,
    render_location_qr_codes,
)
from app.modules.warehouse.location_map.service.map_io import (
    export_warehouse_map,
    get_map_data,
    get_zone_map_layout,
    resolve_map_zip_path,
)
from app.modules.warehouse.location_map.service.map_parser import (
    ParsedShelfNode,
    adapt_kuka_floor_map_to_canvas,
    extract_shelf_nodes_from_zip,
    parse_shelf_node_from_map_node,
)
from app.modules.warehouse.location_map.service.map_query import (
    list_locations_for_map,
    list_locations_for_zone_map,
)
from app.modules.warehouse.location_map.service.map_sync import (
    create_map_metadata,
    import_warehouse_map,
    preview_warehouse_map_import,
    sync_locations_from_map,
)

__all__ = [
    "ParsedShelfNode",
    "adapt_kuka_floor_map_to_canvas",
    "create_map_metadata",
    "delete_location",
    "export_warehouse_map",
    "extract_shelf_nodes_from_zip",
    "generate_qr_location_code",
    "get_location_by_id",
    "get_location_detail",
    "get_locations_by_logic",
    "get_map_data",
    "get_zone_map_layout",
    "import_warehouse_map",
    "list_locations",
    "list_locations_for_map",
    "list_locations_for_zone_map",
    "location_ids_with_assigned_qr",
    "move_assigned_stock_cache",
    "overlay_status_with_assign_cache",
    "parse_shelf_node_from_map_node",
    "preview_warehouse_map_import",
    "render_location_qr_codes",
    "resolve_map_zip_path",
    "sync_locations_from_map",
    "update_location",
    "upsert_location",
]
