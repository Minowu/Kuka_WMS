# Graph Report - KUKA_WMS  (2026-11-01)

## Corpus Check
- 415 files · ~273,399 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 74 file(s) not represented in the graph (top: (none) 52, .csv 3, .css 2)

## Summary
- 3737 nodes · 9427 edges · 191 communities (151 shown, 40 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 850 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2396a25f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sqlalchemy
- index.tsx
- Warehouse Domain (2)
- auth_api.py
- dependencies.py
- NotificationPage.tsx
- ItemDetailPage.tsx
- Location
- get_pda_cnc_stations
- logger.py
- Production Dispatch & AMR Flow (10)
- splitProductConfig.ts
- Warehouse Location & Storage (12)
- Frontend API & Data Services (13)
- Warehouse Domain (14)
- history_schema.py
- Hướng Dẫn Di Chuyển Hệ Thống KUKA_WMS Sang Linux Server
- qrTabletInbound.vi.ts
- ReportPage.tsx
- Production Dispatch & AMR Flow (19)
- InboundStatusTag.tsx
- Mock Print Export Module (21)
- devDependencies
- KeyValueDetailsEditor.tsx
- Warehouse Location & Storage (24)
- inbound_order_schema.py
- inbound_order_api.py
- Outbound Order Service Module (27)
- Context Chuyen Giao Du An Tich Hop Amr Chi Tiet
- StationSettingPage.tsx
- Frontend UI Components (30)
- Frontend React Hooks & State (31)
- Inbound Order Service Module (32)
- get_redis
- Stocktake Service Module (34)
- create_machine
- local-config.yaml
- SkuSearchSelect.tsx
- auth_service.py
- root
- grafana
- CartSelector
- Session
- outbound_order_api.py
- notification_api.py
- useAuth.ts
- Warehouse
- devDependencies
- Bảng Kiểm Kê Cổng WMS & Ma Trận Xung Đột Với KUKA Fleet Manager
- route_api.py
- Frontend UI Components (50)
- apiMessages.vi.ts
- Warehouse Inbound Operations (52)
- detailProgress.ts
- Warehouse Domain (54)
- Warehouse Domain (55)
- RequestLoggingMiddleware
- Warehouse Location & Storage (57)
- Base
- ProductionRoutePage.tsx
- install_db_events
- legacyLotNumber.ts
- location_service.py
- Warehouse Location & Storage (63)
- vite.config.ts
- outbound_order_schema.py
- Warehouse Domain (66)
- WebSocket & Realtime Events (67)
- Celery Deploy
- andon_service.py
- sqlalchemy_dialects
- Warehouse Location & Storage (71)
- README.md
- scripts
- Tsconfig.App Module (75)
- 2. Danh Mục Kiểm Tra Từng Bước (Migration Checklist)
- db_session
- OperatorMapCanvas.tsx
- station_api.py
- dependencies
- useQrCodePrint.ts
- Operational Workflow And Api Design
- Frontend React Hooks & State (83)
- sqlalchemy_orm
- package.json
- Git Commit
- Docker Compose Module (87)
- route_service.py
- useWarehouse.tsx
- config.py
- Tsconfig.Node Module (91)
- 3.2. Phân tích theo 2 kịch bản triển khai
- Docker Compose Module (93)
- 6. Khởi Chạy Hệ Thống & Khôi Phục Dữ Liệu Trên Linux
- robot_celery_task.py
- 2. Sao Chép Mã Nguồn & Xử Lý Định Dạng Ký Tự (CRLF to LF)
- axiosInstance.ts
- 9. Vận Hành, Giới Hạn Dung Lượng Log & Sao Lưu Tự Động
- _ensure_user_can_access_location
- ws_manager.py
- WarehouseMapImportDialog.tsx
- useAppStore
- detect_process
- Docker Compose Module (104)
- Kuka Fleet Migration Plan
- install_celery_signals
- apiErrorMessage.ts
- configure_logging
- backend
- Review Khoi 3 Production Routes And Steps
- OperatorPageHeader.tsx
- celery_app.py
- Default Module (114)
- Prometheus Module (115)
- datasources
- parse_legacy_lot_number
- Docker Compose Module (118)
- Database Pruning And Cleanup Audit
- Kuka Backend Deep Dive Manual
- get_context
- apiError.ts
- install_exception_handlers
- Docker Compose Module (124)
- New Map Format And Grouping Specification
- Review Khoi 2 Product Models Items
- downloadBlobFromResponse
- Prometheus Module (129)
- Database Architecture Design
- Plan Review Khoi 5 Amr Dispatch
- Plan Review Pda Cnc Flow
- Production Station And Workshop Partition Architecture
- Todo
- Outbound Order Model Module (137)
- Docker Compose Module (138)
- Docker Compose Module (139)
- Docker Compose Module (140)
- Docker Compose Module (141)
- Adr 002 Cnc Pda Model Selection And Task Plan
- Explore Khoi 1 Stations And Machines
- alloy
- Review Khoi 1 Stations And Machines
- Summary Context Skill
- prometheus
- ClientLogger
- services
- Review Khoi 5 Amr Dispatch And Queue Worker
- Understand Code
- Kuka Core Database Blueprint
- Adr 001 Deprecate Is Active In Production Stations
- Kuka Core Database Blueprint
- Kuka Full System Review Plan
- Review Khoi 4 Users And Station Rbac
- postgres-exporter
- redis-exporter
- Warehouse Domain (162)
- 02 Legacy Archived Modules Reference
- Readme
- loki
- Plan
- 01 Core Modules And Functions Reference
- Core Database Architecture Specification
- Vite Env.D Module (175)
- Tsconfig Module (176)
- Question
- Readme
- Handoff Summary
- Pyproject Module (194)
- 5. Thiết Lập Mạng Dùng Chung & Cấu Hình Môi Trường (.env)
- database.py
- RobotTask

## God Nodes (most connected - your core abstractions)
1. `Location` - 116 edges
2. `ItemStock` - 111 edges
3. `Item` - 59 edges
4. `react` - 57 edges
5. `User` - 56 edges
6. `FleetTask` - 51 edges
7. `DispatchService` - 48 edges
8. `cn()` - 45 edges
9. `Context Chuyen Giao Du An Tich Hop Amr Chi Tiet` - 45 edges
10. `get_logger()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `1. Bảng Tổng Hợp Lỗi Cấu Hình & Khuyến Nghị Khắc Phục (Issues Audit)` --references--> `root()`  [INFERRED]
  DOCS/deployment/03-pre-migration-checklist.md → backend/app/main.py
- `4. Tóm Tắt Các Điểm Rủi Ro Hàng Đầu Cần Lưu Ý` --references--> `root()`  [INFERRED]
  DOCS/deployment/README.md → backend/app/main.py
- `Giai đoạn 5: Kiểm tra nghiệm thu sau triển khai (Verification Gate)` --references--> `sweep_fleet_tasks()`  [INFERRED]
  DOCS/deployment/03-pre-migration-checklist.md → backend/app/modules/production/production_celery_task.py
- `Giai đoạn 5: Kiểm tra nghiệm thu sau triển khai (Verification Gate)` --references--> `scan_transport_queue()`  [INFERRED]
  DOCS/deployment/03-pre-migration-checklist.md → backend/app/modules/production/production_celery_task.py
- `_location_status_expression()` --uses--> `ItemStock`  [INFERRED]
  backend/app/modules/warehouse/location_map/location_model.py → backend/app/modules/warehouse/item_stock/item_stock_model.py

## Import Cycles
- None detected.

## Communities (191 total, 40 thin omitted)

### Community 0 - "sqlalchemy"
Cohesion: 0.02
Nodes (73): upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade(), downgrade(), upgrade() (+65 more)

### Community 1 - "index.tsx"
Cohesion: 0.11
Nodes (28): AdminRoute(), ProtectedRoute(), PublicRoute(), RoleGatePage(), RoleHomeRedirect(), AdminLayout(), Header(), MainLayout() (+20 more)

### Community 2 - "Warehouse Domain (2)"
Cohesion: 0.04
Nodes (60): AGV_TONE_DOT, AGV_TONE_TEXT, AgvStatusRow, BufferSlotLegend, BufferSlotLegendPanel(), GoodsStatusLegend, GoodsStatusLegendPanel(), PanelShell() (+52 more)

### Community 3 - "auth_api.py"
Cohesion: 0.09
Nodes (31): build_user_access_summary(), resolve_accessible_warehouses(), resolve_user_modules(), resolve_warehouse_scope(), user_is_admin(), user_to_response(), delete_user(), get_me() (+23 more)

### Community 4 - "dependencies.py"
Cohesion: 0.06
Nodes (16): get_db(), get_current_user(), get_dev_admin_user(), require_permission(), require_role(), ClientLogBatch, ClientLogEntry, ingest_client_logs() (+8 more)

### Community 5 - "NotificationPage.tsx"
Cohesion: 0.22
Nodes (12): listNotificationsApi(), resolveNotificationApi(), NOTIFICATION_POLL_INTERVAL_MS, useNotifications(), useNotificationUnsolvedCount(), useResolveNotification(), GetNotificationsParams, Notification (+4 more)

### Community 6 - "ItemDetailPage.tsx"
Cohesion: 0.09
Nodes (47): Button, Card(), DetailFieldSchema, DetailRow(), DetailView(), formatDetailValue(), Form, Input (+39 more)

### Community 7 - "Location"
Cohesion: 0.12
Nodes (25): check_pos_buffer_rule(), _describe(), ensure_location_has_no_stock(), find_map_node(), release_location(), resolve_warehouse_id(), AvailableMachineResponse, MachineCreateRequest (+17 more)

### Community 8 - "get_pda_cnc_stations"
Cohesion: 0.14
Nodes (13): activate_production_route(), create_production_route(), delete_production_route(), get_pda_cnc_stations(), get_pda_models(), get_pda_raw_materials(), get_pda_washing_slots(), get_production_route() (+5 more)

### Community 9 - "logger.py"
Cohesion: 0.07
Nodes (7): bind_context(), clear_context(), DispatchCore, DispatchService, FleetTask, TransportRequest, publish_event()

### Community 10 - "Production Dispatch & AMR Flow (10)"
Cohesion: 0.07
Nodes (44): get_report_kpis(), get_report_stock_aging_bucket(), get_report_stock_aging_overview(), get_report_top_products(), get_report_trends(), snapshot_inventory_daily_task(), ReportKpiResponse, ReportStockAgingBucketResponse (+36 more)

### Community 11 - "splitProductConfig.ts"
Cohesion: 0.15
Nodes (17): canUseSplitProductForQrType(), isSplitProductQrType(), isSplitProductWarehouse(), normalizeSplitProductQrType(), shouldAutoCheckSplitProduct(), shouldRunSplitStockGate(), shouldShowSplitProductToggle(), SPLIT_PRODUCT_QR_TYPES (+9 more)

### Community 12 - "Warehouse Location & Storage (12)"
Cohesion: 0.06
Nodes (57): buildLocationMapParams(), buildMapImportFormData(), DEFAULT_MAP_LOCATION_TYPE, downloadActiveMapApi(), getActiveMapApi(), getActiveMapMetadataApi(), getActiveWarehouseMapApi(), getFullLocationsApi() (+49 more)

### Community 13 - "Frontend API & Data Services (13)"
Cohesion: 0.08
Nodes (42): convert_item_quantity(), create_item_unit(), create_unit(), delete_item_unit(), delete_unit(), get_item_unit(), get_item_units_by_item(), get_unit() (+34 more)

### Community 14 - "Warehouse Domain (14)"
Cohesion: 0.05
Nodes (62): analyze_items(), create_item(), delete_item(), download_last_import_item_file(), get_import_items_job(), get_item(), import_items_masan(), list_items() (+54 more)

### Community 15 - "history_schema.py"
Cohesion: 0.07
Nodes (32): create_history(), create_transaction(), get_history(), get_transaction(), get_transaction_history(), list_histories(), list_transactions(), History (+24 more)

### Community 16 - "Hướng Dẫn Di Chuyển Hệ Thống KUKA_WMS Sang Linux Server"
Cohesion: 0.17
Nodes (12): 10. Kế Hoạch Lùi Bước Khẩn Cấp (Rollback Plan), 1.1. Cấu hình phần cứng máy chủ Linux đề xuất, 1.2. Cài đặt Docker Engine & Docker Compose Plugin trên Linux, 1. Yêu Cầu Tiên Quyết (Prerequisites), 3. Phân Quyền Thư Mục Trên Linux (Directory Permissions & UID), 4.1. Bước 1: Sao lưu PostgreSQL từ máy Windows, 4.2. Bước 2: Sao lưu Redis AOF / RDB từ máy Windows, 4. Di Chuyển Dữ Liệu Sản Xuất (Data Migration) (+4 more)

### Community 18 - "ReportPage.tsx"
Cohesion: 0.08
Nodes (47): getReportKpisApi(), getReportStockAgingBucketApi(), getReportStockAgingOverviewApi(), getReportTopProductsApi(), getReportTrendsApi(), REPORT_KPI_POLL_INTERVAL_MS, useReportKpis(), useReportStockAging() (+39 more)

### Community 19 - "Production Dispatch & AMR Flow (19)"
Cohesion: 0.07
Nodes (3): _ics_configured(), KukaFleetClient, WebhookHandler

### Community 20 - "InboundStatusTag.tsx"
Cohesion: 0.19
Nodes (11): InboundStatusTag(), InboundStatusTagProps, SIZE_STYLES, STATUS_STYLES, OutboundStatusTag(), OutboundStatusTagProps, SIZE_STYLES, STATUS_STYLES (+3 more)

### Community 21 - "Mock Print Export Module (21)"
Cohesion: 0.07
Nodes (23): _bacviet_labels_from_payload(), build_bacviet_payload(), build_location_payload(), build_location_payload_from_zone(), build_transfer_payload(), export_bacviet_xlsx(), export_location_xlsx(), export_pdf() (+15 more)

### Community 22 - "devDependencies"
Cohesion: 0.15
Nodes (12): eslint@^10.5.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.5.2, globals@^17.6.0, typescript-eslint@^8.59.2, eslint, @eslint/js (+4 more)

### Community 23 - "KeyValueDetailsEditor.tsx"
Cohesion: 0.39
Nodes (6): KeyValueDetailsEditor(), KeyValueDetailsEditorProps, createEmptyKeyValueEntry(), detailsToEntries(), KeyValueEntry, nextKeyValueEntryId()

### Community 24 - "Warehouse Location & Storage (24)"
Cohesion: 0.09
Nodes (37): getAllItemStockByZoneApi(), getAllLocationsByZoneApi(), getItemStockByZoneApi(), getLocationsByZoneApi(), listStorageLocationsApi(), listStorageRelocateCommandsApi(), relocateStorageStockApi(), itemStockByZoneQueryKey() (+29 more)

### Community 25 - "inbound_order_schema.py"
Cohesion: 0.07
Nodes (37): release_inbound_locations(), relocate_assigned_stocks(), AssignedItemStockResponse, AssignItemStockMetaResponse, AssignOrGetItemStockResponse, AssignPackingToItemRequest, CacheForPackingUserRequest, InboundCallerResponse (+29 more)

### Community 26 - "inbound_order_api.py"
Cohesion: 0.12
Nodes (25): accept_inbound_task_task(), caller_inbound_order_task(), create_inbound_order_task(), _dump(), get_inbound_order_details_task(), update_inbound_order_task(), accept_inbound_task(), assign_or_get_item_stocks() (+17 more)

### Community 27 - "Outbound Order Service Module (27)"
Cohesion: 0.12
Nodes (43): OutboundOrder, OutboundOrderAllocation, OutboundOrderDetail, _build_allocation_response(), _build_detail_response(), _build_manual_allocation_task_from_group(), _build_outbound_list_summary(), calculate_outbound_order() (+35 more)

### Community 28 - "Context Chuyen Giao Du An Tich Hop Amr Chi Tiet"
Cohesion: 0.04
Nodes (46): 0. Cách đọc tài liệu và nguyên tắc quan trọng, 10. Nguyên tắc thiết kế để tránh lỗi, 11.1 Ba câu hỏi ưu tiên, 11.2 Checklist kỹ thuật tiếp theo, 11. Tích hợp AMR — cần xác minh với nhà cung cấp, 12. Câu hỏi nghiệp vụ còn mở, 13. Những điều làm rõ gần nhất, 14. Demo HTML hiện có và giới hạn (+38 more)

### Community 29 - "StationSettingPage.tsx"
Cohesion: 0.11
Nodes (35): createMachineApi(), deleteMachineApi(), getMachinesApi(), getUserLocationsApi(), updateMachineApi(), updateUserLocationsApi(), createStationLocationApi(), deleteStationLocationApi() (+27 more)

### Community 30 - "Frontend UI Components (30)"
Cohesion: 0.10
Nodes (40): ADR-0002, refreshAccessTokenApi(), CallMaterialPayload, callMaterialToCncApi(), completeMachiningStageApi(), CompleteStagePayload, getPdaCncStationsApi(), getPdaModelsApi() (+32 more)

### Community 31 - "Frontend React Hooks & State (31)"
Cohesion: 0.09
Nodes (42): analyzeItemsApi(), createItemApi(), createQrCodesApi(), deactivateItemApi(), downloadLastImportItemFileApi(), generateQrCodesApi, getItemByIdApi(), getItemImportJobApi() (+34 more)

### Community 32 - "Inbound Order Service Module (32)"
Cohesion: 0.14
Nodes (30): cache_delete(), InboundOrder, InboundOrderAllocation, InboundOrderDetail, _build_allocation_response(), _build_detail_response(), _build_inbound_list_summary(), caller_inbound_order() (+22 more)

### Community 33 - "get_redis"
Cohesion: 0.10
Nodes (39): cache_delete_pattern(), cache_exists(), cache_get(), cache_scan_keys(), cache_set(), close_redis(), get_redis(), _log_redis_errors() (+31 more)

### Community 34 - "Stocktake Service Module (34)"
Cohesion: 0.10
Nodes (36): lot_string_to_date(), update_stocktake(), Stocktake, _stocktake_all_items_status(), _stocktake_has_any_item(), _stocktake_has_item_status(), _stocktake_item_exists(), StocktakeItemStock (+28 more)

### Community 35 - "create_machine"
Cohesion: 0.17
Nodes (5): create_machine(), delete_machine(), get_machine(), list_available_machines(), update_machine()

### Community 36 - "local-config.yaml"
Cohesion: 0.05
Nodes (39): analytics, reporting_enabled, auth_enabled, common, instance_addr, path_prefix, replication_factor, ring (+31 more)

### Community 37 - "SkuSearchSelect.tsx"
Cohesion: 0.26
Nodes (10): closeOtherSkuSelects(), formatQuantityHint(), ItemQueryParams, openSkuSelectRegistry, registerOpenSkuSelect(), SkuSearchOption, SkuSearchSelect(), SkuSearchSelectProps (+2 more)

### Community 38 - "auth_service.py"
Cohesion: 0.15
Nodes (33): create_access_token(), create_refresh_token(), decode_refresh_token(), get_password_hash(), verify_password(), Permission, Role, RolePermission (+25 more)

### Community 39 - "root"
Cohesion: 0.18
Nodes (8): health(), root(), 1. Mục Tiêu & Phạm Vi (Scope & Objectives), 2. Bản Đồ Tài Liệu (Documentation Roadmap), 3. Kiến Trúc Triển Khai Hệ Thống KUKA_WMS Trên Linux, 4. Tóm Tắt Các Điểm Rủi Ro Hàng Đầu Cần Lưu Ý, Chi tiết từng tài liệu:, Tài Liệu Triển Khai & Di Chuyển Hệ Thống KUKA_WMS Sang Linux

### Community 40 - "grafana"
Cohesion: 0.18
Nodes (11): GF_SECURITY_ADMIN_PASSWORD, GF_SECURITY_ADMIN_USER, GF_USERS_ALLOW_SIGN_UP, container_name, depends_on, environment, image, ports (+3 more)

### Community 41 - "CartSelector"
Cohesion: 0.08
Nodes (3): CartSelector, QueueService, TestCartSelectorSameMachine

### Community 42 - "Session"
Cohesion: 0.11
Nodes (18): update_location(), LocationUpdate, _active_stock_totals(), _apply_shelf_to_location(), _assign_node_numbers(), _blocked_message(), _dedupe_shelves(), delete_location() (+10 more)

### Community 43 - "outbound_order_api.py"
Cohesion: 0.16
Nodes (14): calculate_outbound_order(), confirm_outbound_order_no_qr(), confirm_outbound_order_qr(), create_outbound_order(), delete_outbound_order(), execute_outbound_qr_manual(), execute_outbound_task(), get_outbound_lacked_details() (+6 more)

### Community 44 - "notification_api.py"
Cohesion: 0.13
Nodes (20): create_notification(), delete_notification(), get_notification(), list_notifications(), resolve_notification(), update_notification(), check_long_holding_stock_task(), NotificationCreate (+12 more)

### Community 45 - "useAuth.ts"
Cohesion: 0.10
Nodes (29): @tanstack/react-query@^5.101.0, createUserApi(), deleteUserApi(), getUserApi(), getUsersApi(), loginApi(), updateUserApi(), refreshClient (+21 more)

### Community 46 - "Warehouse"
Cohesion: 0.19
Nodes (15): create_warehouse(), delete_warehouse(), get_warehouse(), list_warehouses(), update_warehouse(), Warehouse, WarehouseCreate, WarehouseListResponse (+7 more)

### Community 47 - "devDependencies"
Cohesion: 0.11
Nodes (19): devDependencies, autoprefixer@^10.5.0, postcss@^8.5.15, prettier@^3.8.4, tailwindcss@^4.3.1, @types/node@^24.12.3, @types/react@^19.2.14, @types/react-dom@^19.2.3 (+11 more)

### Community 48 - "Bảng Kiểm Kê Cổng WMS & Ma Trận Xung Đột Với KUKA Fleet Manager"
Cohesion: 0.29
Nodes (7): 1.1. Bảng tổng hợp cổng từ cấu hình mã nguồn và Docker Compose, 1.2. Hiện trạng lắng nghe thực tế trên máy Windows (Live Listeners Audit), 1. Bảng Kiểm Kê Toàn Bộ Cổng Mạng Của KUKA_WMS, 2. Danh Sách Cổng Của KUKA Fleet Manager Cần Tránh, 4. Kế Hoạch Phân Bổ Cổng Chuẩn Hóa Trên Linux Production, 5. Tóm Tắt Quy Tắc Vàng Khi Cấu Hình Cổng (Golden Rules), Bảng Kiểm Kê Cổng WMS & Ma Trận Xung Đột Với KUKA Fleet Manager

### Community 49 - "route_api.py"
Cohesion: 0.19
Nodes (17): CallMaterialRequest, CompleteStageRequest, ContainerActionRequest, PdaCncStation, PdaCncStationRack, PdaCncSupportedModel, PdaModelItem, PdaRawMaterialSlot (+9 more)

### Community 50 - "Frontend UI Components (50)"
Cohesion: 0.17
Nodes (21): assignZoneLocationsApi(), createZoneApi(), deleteZoneApi(), listLocationsApi(), listZonesApi(), printLocationQrCodesApi(), updateZoneApi(), useAssignZoneLocations() (+13 more)

### Community 51 - "apiMessages.vi.ts"
Cohesion: 0.20
Nodes (16): API_MESSAGE_ENTRIES, API_MESSAGES_VI, applyDictionary(), translateAnchorPackItemMismatch(), translateApiMessage(), translateInvalidCavity(), translateItemNotFound(), translateOnlyItemQrLocationAssign() (+8 more)

### Community 52 - "Warehouse Inbound Operations (52)"
Cohesion: 0.13
Nodes (31): apply_lot_display_fields(), format_lot_number_display(), format_lot_part_for_display(), format_lot_value_for_display(), resolve_lot_number_input(), AssignOrGetItemStockAction, _apply_split_flag_to_cache_payload(), assign_for_packing_user() (+23 more)

### Community 54 - "Warehouse Domain (54)"
Cohesion: 0.15
Nodes (21): create_item_stock(), delete_item_stock(), get_item_stock(), get_stock_split(), list_item_stocks(), update_item_stock(), ItemStockCreate, ItemStockListResponse (+13 more)

### Community 55 - "Warehouse Domain (55)"
Cohesion: 0.10
Nodes (34): WarehouseMapCanvas(), WarehouseMapCanvasProps, LEGEND_ITEMS, WarehouseMapLegend(), WarehouseMapToolbar(), WarehouseMapToolbarProps, WarehouseMapZoomControls(), WarehouseMapZoomControlsProps (+26 more)

### Community 57 - "Warehouse Location & Storage (57)"
Cohesion: 0.16
Nodes (20): delete_location(), export_warehouse_map(), get_location(), get_location_detail(), get_map_data(), get_zone_map_data(), import_warehouse_map(), list_locations() (+12 more)

### Community 59 - "ProductionRoutePage.tsx"
Cohesion: 0.18
Nodes (24): activateProductionRouteApi(), createProductionRouteApi(), deleteProductionRouteApi(), getAvailableMachinesApi(), getProductionRouteDetailApi(), getProductionRoutesApi(), updateProductionRouteApi(), useItems() (+16 more)

### Community 61 - "legacyLotNumber.ts"
Cohesion: 0.09
Nodes (32): aggregateLotNumbers(), COMPACT6, COMPACT_RANGE_RE, COMPACT_SINGLE_RE, compareLotDates(), formatLotNumberDisplay(), formatLotPartForDisplay(), formatLotValueForDisplay() (+24 more)

### Community 62 - "location_service.py"
Cohesion: 0.13
Nodes (19): is_manual_warehouse(), LocationListResponse, LocationsForMapResponse, MapLocationItem, MapLocationStockItem, generate_qr_location_code(), list_locations(), list_locations_for_map() (+11 more)

### Community 63 - "Warehouse Location & Storage (63)"
Cohesion: 0.11
Nodes (16): WarehouseMap, MapCreate, MapDataResponse, adapt_kuka_floor_map_to_canvas(), create_map_metadata(), export_warehouse_map(), extract_shelf_nodes_from_zip(), _extract_shelves_from_kuka_floor_map() (+8 more)

### Community 64 - "vite.config.ts"
Cohesion: 0.20
Nodes (8): @tailwindcss/vite@^4.3.1, vite@8.1.5, vite-plugin-node-polyfills@^0.28.0, @vitejs/plugin-react@6.0.4, @tailwindcss/vite, vite, vite-plugin-node-polyfills, @vitejs/plugin-react

### Community 65 - "outbound_order_schema.py"
Cohesion: 0.11
Nodes (26): AllocationOutboundTaskExecute, AllocationResult, CalculateOutboundDetail, CalculateOutboundResponse, DetailForCalculate, ExecuteQrManualRequest, ExecuteQrManualResponse, LackedDetailResponse (+18 more)

### Community 66 - "Warehouse Domain (66)"
Cohesion: 0.12
Nodes (24): MapData, assignFocusNodesToGrid(), boundsFromFocusNodes(), buildKeyIndex(), computeMapContentBounds(), computeOperatorGridMetrics(), computeOperatorMapViewport(), computeOperatorVirtualGridLayout() (+16 more)

### Community 68 - "Celery Deploy"
Cohesion: 0.08
Nodes (26): 0. Checklist tổng quan, 10. Service tùy chọn: beat và flower, 11. `backend/.env`, 1. `backend/requirements.txt`, 2. `backend/pyproject.toml`, 3. `backend/app/core/config.py`, 4. Tạo mới `backend/app/core/celery_app.py`, 4xx từ ICS = payload sai, retry vô nghĩa (+18 more)

### Community 69 - "andon_service.py"
Cohesion: 0.21
Nodes (5): get_andon_raw_material_queue(), AndonRawMaterialDemand, AndonRawMaterialResponse, AndonRawSlotStatus, get_raw_material_andon_queue()

### Community 70 - "sqlalchemy_dialects"
Cohesion: 0.11
Nodes (9): downgrade(), upgrade(), upgrade(), downgrade(), upgrade(), downgrade(), upgrade(), downgrade() (+1 more)

### Community 71 - "Warehouse Location & Storage (71)"
Cohesion: 0.14
Nodes (18): LocationCreate, LocationDetailResponse, LocationDetailStockItem, LocationDetailSummary, LocationQrPrintResponse, MapRemapEntry, MapSyncCounts, MapSyncCreatedItem (+10 more)

### Community 73 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

### Community 75 - "Tsconfig.App Module (75)"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, erasableSyntaxOnly, ignoreDeprecations, jsx, lib, module (+13 more)

### Community 76 - "2. Danh Mục Kiểm Tra Từng Bước (Migration Checklist)"
Cohesion: 0.33
Nodes (6): 2. Danh Mục Kiểm Tra Từng Bước (Migration Checklist), Giai đoạn 1: Chuẩn bị mã nguồn & Sửa cấu hình (Pre-flight Config Fixes), Giai đoạn 2: Chuẩn bị máy chủ đích Linux (Server Preparation), Giai đoạn 3: Sao chép & Chuyển đổi dữ liệu (Data & Source Transfer), Giai đoạn 4: Triển khai & Khôi phục CSDL (Deployment & Restore), Giai đoạn 6: Thiết lập vận hành tự động (Maintenance Setup)

### Community 77 - "db_session"
Cohesion: 0.45
Nodes (11): db_session(), calculate_outbound_order_task(), create_outbound_order_task(), _dump(), execute_outbound_task_task(), get_outbound_lacked_details_task(), get_outbound_manual_allocation_tasks_task(), get_outbound_order_by_id_task() (+3 more)

### Community 78 - "OperatorMapCanvas.tsx"
Cohesion: 0.07
Nodes (36): formatEmptyLocationLabel(), formatStorageLocationLabel(), getZoneMapStatusApi(), BufferCellClickPayload, BufferMapCanvasTuning, computeMapSizeFromNodes(), drawInboundSeparator(), drawSelectedHighlight() (+28 more)

### Community 79 - "station_api.py"
Cohesion: 0.17
Nodes (13): create_station_location(), delete_station_location(), get_available_map_nodes(), get_station_catalog(), update_station_location(), MachineCatalogGroup, MapAvailableNodeResponse, StationCatalogItem (+5 more)

### Community 80 - "dependencies"
Cohesion: 0.09
Nodes (22): dependencies, @ant-design/icons@^6.2.5, antd@^6.4.4, axios@^1.18.0, date-fns@^4.4.0, dayjs@^1.11.21, @hookform/resolvers@^5.4.0, jsqr@^1.4.0 (+14 more)

### Community 81 - "useQrCodePrint.ts"
Cohesion: 0.13
Nodes (20): INBOUND_MANUAL_WAREHOUSE_IDS, INBOUND_TYPE, isManualPrintWarehouse(), OUTBOUND_MANUAL_WAREHOUSE_IDS, OUTBOUND_TYPE, QR_PRINT_LABELS_PER_PAGE_AUTO, QR_PRINT_LABELS_PER_PAGE_MANUAL, resolveInboundLotValidation() (+12 more)

### Community 82 - "Operational Workflow And Api Design"
Cohesion: 0.11
Nodes (19): 1. Quét các yêu cầu chờ xe CNC theo thứ tự ưu tiên & FIFO, 1. TỔNG QUAN KIẾN TRÚC VẬN HÀNH & NGUYÊN TẮC CỐT LÕI, 2. SƠ ĐỒ TUẦN TỰ NGHIỆP VỤ (MERMAID SEQUENCE DIAGRAMS), 3. ĐẶC TẢ CHI TIẾT RESTful API, 4. WEBSOCKET REALTIME SPECIFICATION, 5. FLEET MANAGER ADAPTER INTEGRATION (KUKA RCS), 6. CƠ CHẾ ENGINE HÀNG ĐỢI TỰ ĐỘNG (QUEUE PROCESSOR ENGINE), 7. BẢNG TỔNG KẾT & DANH MỤC TRƯỜNG DỮ LIỆU ĐỐI SOÁT (+11 more)

### Community 83 - "Frontend React Hooks & State (83)"
Cohesion: 0.23
Nodes (16): createNodeApi(), deleteNodeApi(), listNodesApi(), updateNodeApi(), invalidateNodes(), nodesQueryKey(), useCreateNode(), useDeleteNode() (+8 more)

### Community 84 - "sqlalchemy_orm"
Cohesion: 0.07
Nodes (17): get_logger(), log_context(), fail_and_release(), IcsError, enqueue_fleet_submit(), persist_task_status(), scan_transport_queue(), submit_fleet_task() (+9 more)

### Community 85 - "package.json"
Cohesion: 0.18
Nodes (10): html5-qrcode@^2.3.8, react-dom@^19.2.6, xlsx-js-style@^1.2.0, name, private, type, version, html5-qrcode (+2 more)

### Community 86 - "Git Commit"
Cohesion: 0.11
Nodes (19): Also check status, Best Practices, BREAKING CHANGE footer, Breaking Changes, Commit Types, Conventional Commit Format, Git Commit, Exclamation mark after type/scope (+11 more)

### Community 87 - "Docker Compose Module (87)"
Cohesion: 0.20
Nodes (11): VITE_API_URL, build, args, context, dockerfile, build, container_name, depends_on (+3 more)

### Community 88 - "route_service.py"
Cohesion: 0.30
Nodes (13): ItemSummary, ProductionRouteDetailResponse, ProductionRouteResponse, RouteStepResponse, activate_route(), create_route(), delete_route(), _get_or_create_machine() (+5 more)

### Community 89 - "useWarehouse.tsx"
Cohesion: 0.16
Nodes (21): createWarehouseApi(), deleteWarehouseApi(), listWarehousesApi(), updateWarehouseApi(), CardItem, Hero(), HeroProps, warehouseLabel() (+13 more)

### Community 90 - "config.py"
Cohesion: 0.29
Nodes (3): _parse_int_id_list(), Settings, Config

### Community 91 - "Tsconfig.Node Module (91)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 92 - "3.2. Phân tích theo 2 kịch bản triển khai"
Cohesion: 0.40
Nodes (5): 3.1. Bảng so khớp trực tiếp giữa Cổng WMS và Cổng KUKA Fleet, 3.2. Phân tích theo 2 kịch bản triển khai, 3. Ma Trận So Khớp & Đánh Giá Xung Đột (Conflict Matrix), Kịch bản A: Chạy CÙNG MÁY CHỦ (Co-located / Same Host với KUKA Fleet Manager), Kịch bản B: Chạy KHÁC MÁY CHỦ (Dedicated Host riêng trên mạng xưởng LAN)

### Community 93 - "Docker Compose Module (93)"
Cohesion: 0.12
Nodes (16): command, container_name, environment, healthcheck, image, ports, restart, volumes (+8 more)

### Community 94 - "6. Khởi Chạy Hệ Thống & Khôi Phục Dữ Liệu Trên Linux"
Cohesion: 0.40
Nodes (5): 6.1. Khởi động CSDL PostgreSQL và Redis trước, 6.2. Khôi phục dữ liệu vào CSDL `WMS_db`, 6.3. Khôi phục dữ liệu Redis (Tùy chọn), 6.4. Khởi chạy toàn bộ hệ sinh thái KUKA_WMS, 6. Khởi Chạy Hệ Thống & Khôi Phục Dữ Liệu Trên Linux

### Community 96 - "2. Sao Chép Mã Nguồn & Xử Lý Định Dạng Ký Tự (CRLF to LF)"
Cohesion: 0.50
Nodes (4): 2.1. Đóng gói mã nguồn từ máy Windows, 2.2. Chuyển file sang máy chủ Linux và giải nén, 2.3. Chuyển đổi định dạng ký tự kết thúc dòng (CRLF sang LF), 2. Sao Chép Mã Nguồn & Xử Lý Định Dạng Ký Tự (CRLF to LF)

### Community 97 - "axiosInstance.ts"
Cohesion: 0.06
Nodes (33): getRawMaterialAndonQueueApi(), axiosInstance, CustomAxiosRequestConfig, failedQueue, App(), AppContent(), queryClient, ErrorBoundary (+25 more)

### Community 98 - "9. Vận Hành, Giới Hạn Dung Lượng Log & Sao Lưu Tự Động"
Cohesion: 0.50
Nodes (4): 9.1. Giới hạn dung lượng Log của Docker Daemon (Log Rotation), 9.2. Tự động dọn dẹp file log ứng dụng (`backend/logs/*.jsonl`), 9.3. Kịch bản sao lưu CSDL tự động hằng ngày (Automated Backup Script), 9. Vận Hành, Giới Hạn Dung Lượng Log & Sao Lưu Tự Động

### Community 99 - "_ensure_user_can_access_location"
Cohesion: 0.15
Nodes (7): call_material(), complete_machining_stage(), _ensure_user_can_access_location(), _get_recent_location_error(), receive_task_status(), register_rack_at_raw_material(), return_empty_cart_from_washing()

### Community 100 - "ws_manager.py"
Cohesion: 0.20
Nodes (3): decode_access_token(), _authenticate_ws_token(), websocket_endpoint()

### Community 101 - "WarehouseMapImportDialog.tsx"
Cohesion: 0.29
Nodes (10): binLabel(), extractErrorDetail(), referenceSummary(), totalReferences(), WarehouseMapImportDialog(), WarehouseMapImportDialogProps, useImportWarehouseMap(), usePreviewWarehouseMapImport() (+2 more)

### Community 102 - "useAppStore"
Cohesion: 0.16
Nodes (14): resolveInboundType(), resolveOutboundType(), syncWarehouseOperationTypes(), WarehouseOperationType, formatDate(), NotificationPage(), renderSeverityTag(), rowClassName() (+6 more)

### Community 103 - "detect_process"
Cohesion: 0.22
Nodes (4): ConsoleFormatter, ContextFilter, detect_process(), JsonFormatter

### Community 104 - "Docker Compose Module (104)"
Cohesion: 0.15
Nodes (12): command, container_name, image, ports, restart, volumes, services, redis (+4 more)

### Community 105 - "Kuka Fleet Migration Plan"
Cohesion: 0.10
Nodes (20): 0. CÁC QUYẾT ĐỊNH ĐÃ CHỐT, 10. THỨ TỰ THỰC HIỆN & COMMIT, 1. CẤU HÌNH (`backend/app/core/config.py`), 2. QUY TẮC SINH MÃ, 3. THAY ĐỔI CƠ SỞ DỮ LIỆU (1 migration Alembic mới), 4. OUTBOUND ADAPTER (`dispatch_service.py`), 5. KHÓA CONTAINER: ĐÁNH GIÁ ĐỀ XUẤT "KHÓA TỪ MOVE_BEGIN", 6. INBOUND WEBHOOK `POST /api/v1/receive-status` (+12 more)

### Community 106 - "install_celery_signals"
Cohesion: 0.36
Nodes (8): request_scope(), install_celery_signals(), _beat_init(), _chan(), _failure(), _postrun(), _prerun(), _retry()

### Community 107 - "apiErrorMessage.ts"
Cohesion: 0.39
Nodes (8): isQrTypeLocationConflictMessage(), cleanMessage(), extractDetailMessages(), extractRawDetailMessage(), FIELD_LABELS, fieldLabelFromLoc(), formatValidationItem(), isQrTypeLocationConflictError()

### Community 109 - "configure_logging"
Cohesion: 0.29
Nodes (3): configure_logging(), setup_logger(), _setup_logging()

### Community 110 - "backend"
Cohesion: 0.25
Nodes (8): command, container_name, env_file, image, ports, restart, volumes, backend

### Community 111 - "Review Khoi 3 Production Routes And Steps"
Cohesion: 0.18
Nodes (11): 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW), 1. Tắt active toàn bộ các route khác của cùng Model, 2. Bật active cho route này, 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 3 (INVOLVED FILES), 🔍 3. CHI TIẾT CÁC LUỒNG THAO TÁC CỤ THỂ, 🗄️ 4. TỪ ĐIỂN DỮ LIỆU & KIẾN TRÚC 3NF (DATA DICTIONARY), ⚙️ 5. CƠ CHẾ KẾT NỐI VỚI LÕI ĐIỀU PHỐI AMR (DISPATCH ENGINE INTEGRATION), ⚠️ 6. ĐÁNH GIÁ CHẤT LƯỢNG MÃ NGUỒN & CÁC ĐIỂM CẦN CHUẨN HÓA (+3 more)

### Community 112 - "OperatorPageHeader.tsx"
Cohesion: 0.32
Nodes (6): OperatorMetricItem, OperatorPageHeader(), OperatorPageHeaderProps, OperatorShellContext, OperatorShellContextValue, useOperatorShell()

### Community 114 - "Default Module (114)"
Cohesion: 0.18
Nodes (10): apiVersion, path, providers, disableDeletion, folder, name, options, orgId (+2 more)

### Community 115 - "Prometheus Module (115)"
Cohesion: 0.18
Nodes (10): global, evaluation_interval, scrape_interval, service, scrape_configs, job_name, metrics_path, static_configs (+2 more)

### Community 116 - "datasources"
Cohesion: 0.18
Nodes (10): apiVersion, datasources, access, editable, jsonData, name, type, uid (+2 more)

### Community 117 - "parse_legacy_lot_number"
Cohesion: 0.60
Nodes (4): parse_legacy_lot_number(), slash_to_compact(), to_compact(), validate_ddmmyy()

### Community 118 - "Docker Compose Module (118)"
Cohesion: 0.56
Nodes (10): environment, environment, environment, environment, environment, CELERY_BROKER_RESULT_URL, CELERY_BROKER_URL, DATABASE_URL (+2 more)

### Community 119 - "Database Pruning And Cleanup Audit"
Cohesion: 0.20
Nodes (10): 1. TỔNG QUAN HIỆN TRẠNG 39 BẢNG TRONG CƠ SỞ DỮ LIỆU, 2. ĐÁNH GIÁ MỨC ĐỘ SỬ DỤNG & SỰ PHỤ THUỘC (DEPENDENCY CHECK), 3. PHÂN LOẠI CHI TIẾT & BẢNG ĐỐI SOÁNH NGUYÊN NHÂN (RETENTION & PRUNING MATRIX), 4. PHÂN TÍCH RỦI RO & CÁC ĐIỂM NGHẼN KHI THÁO GỠ (RISK & COUPLING AUDIT), 5. LỘ TRÌNH TINH LỌC AN TOÀN 4 GIAI ĐOẠN (SAFE PRUNING ROADMAP), 6. KẾT LUẬN & ĐỀ XUẤT HÀNH ĐỘNG TIẾP THEO, BÁO CÁO KIỂM TOÁN CƠ SỞ DỮ LIỆU & MÃ NGUỒN (DATABASE & CODEBASE PRUNING AUDIT), Database Pruning And Cleanup Audit (+2 more)

### Community 120 - "Kuka Backend Deep Dive Manual"
Cohesion: 0.20
Nodes (10): CẨM NANG GIẢI PHẪU TOÀN DIỆN KIẾN TRÚC BACKEND & CƠ CHẾ VẬN HÀNH KUKA AMR, Kuka Backend Deep Dive Manual, PHẦN 1: TỔNG QUAN KIẾN TRÚC & BỐ CỤC THƯ MỤC (`backend/app/`), PHẦN 2: CÁC TIẾN TRÌNH CHẠY NGẦM (DAEMONS & BACKGROUND WORKERS), PHẦN 3: GIẢI PHẪU CHI TIẾT ĐỘNG CƠ ĐIỀU PHỐI (`dispatch_service.py` - 25 HÀM), PHẦN 4: CÁC ENDPOINT THỰC THI CHO PDA 4.2" CẦM TAY (`route_api.py`), PHẦN 5: MODULE QUY TRÌNH SẢN XUẤT 3NF (`route_service.py`), PHẦN 6: CÁC MODULE VỆ TINH TRONG HỆ THỐNG (`warehouse/` & `auth/`) (+2 more)

### Community 121 - "get_context"
Cohesion: 0.40
Nodes (3): _channel_overrides(), get_context(), _before_publish()

### Community 122 - "apiError.ts"
Cohesion: 0.50
Nodes (4): ApiErrorResponse, ApiValidationErrorItem, formatApiErrorDetail(), getApiErrorDetail()

### Community 124 - "Docker Compose Module (124)"
Cohesion: 0.33
Nodes (9): depends_on, depends_on, depends_on, depends_on, depends_on, condition, db, redis (+1 more)

### Community 125 - "New Map Format And Grouping Specification"
Cohesion: 0.22
Nodes (9): 1. FIFO cho Level 0: Ưu tiên xe nạp vào sàn sớm nhất, 1. TỔNG QUAN & BỐI CẢNH (OVERVIEW & OBJECTIVES), 2. Euclidean 2D Distance cho Level > 0 (trung chuyển giữa các máy CNC), 2. PHÂN TÍCH SO SÁNH ĐỊNH DẠNG BẢN ĐỒ (LEGACY VS. KUKA V2), 3. THIẾT KẾ & NÂNG CẤP DATABASE, 4. BỘ CHUYỂN ĐỔI BẢN ĐỒ (MAP ADAPTER & PARSER ENGINE), 5. THUẬT TOÁN ĐIỀU PHỐI (FIFO LEVEL 0 VS. EUCLIDEAN DISTANCE LEVEL > 0), 6. KẾT QUẢ KIỂM THỬ & XÁC MINH (VERIFICATION) (+1 more)

### Community 126 - "Review Khoi 2 Product Models Items"
Cohesion: 0.22
Nodes (9): 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW), 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 2 (INVOLVED FILES), 🔍 3. CHI TIẾT CÁC LUỒNG THAO TÁC CỤ THỂ, 🗄️ 4. TỪ ĐIỂN DỮ LIỆU & RÀNG BUỘC CƠ SỞ DỮ LIỆU (DATA DICTIONARY), 🔗 5. MA TRẬN LIÊN KẾT GIỮA CÁC KHỐI TRONG HỆ THỐNG, ⚠️ 6. ĐÁNH GIÁ CHẤT LƯỢNG MÃ NGUỒN & CÁC ĐIỂM CẦN CHUẨN HÓA, 🧪 7. MA TRẬN KIỂM THỬ & TIÊU CHÍ NGHIỆM THU (TEST CRITERIA), Review Khoi 2 Product Models Items (+1 more)

### Community 127 - "downloadBlobFromResponse"
Cohesion: 0.83
Nodes (3): downloadBlobFromResponse(), parseFilenameFromContentDisposition(), triggerBlobDownload()

### Community 129 - "Prometheus Module (129)"
Cohesion: 0.22
Nodes (8): apiVersion, datasources, access, editable, isDefault, name, type, url

### Community 131 - "Database Architecture Design"
Cohesion: 0.25
Nodes (8): 1. TỔNG QUAN HỆ THỐNG & NGUYÊN TẮC THIẾT KẾ, 2. PHẦN 1: PHÂN TÍCH DATABASE HIỆN TẠI (WMS CŨ - 30 BẢNG), 3. PHẦN 2: THIẾT KẾ DATABASE MỚI CHO DÂY CHUYỀN KUKA AMR, Database Architecture Design, HỆ THỐNG ĐIỀU PHỐI KUKA AMR CHO DÂY CHUYỀN SẢN XUẤT CƠ KHÍ & GIA CÔNG CNC, MỤC LỤC, TÀI LIỆU THIẾT KẾ KIẾN TRÚC CƠ SỞ DỮ LIỆU (DATABASE ARCHITECTURE DESIGN), TỔNG KẾT VÀ BÀN GIAO TIẾP THEO

### Community 132 - "Plan Review Khoi 5 Amr Dispatch"
Cohesion: 0.25
Nodes (8): 1. Sơ đồ luồng tổng thể (Sequence Diagram), 2. Hình minh họa kiến trúc điều phối xưởng (Wireframe & Concept), 3. Tổng hợp các file tham gia trong Khối 5, 4. Chi tiết các viễn cảnh vận hành & Thuật toán lõi, 5. Đánh giá chất lượng mã nguồn & Điểm mạnh, 6. Các hạn chế còn tồn tại & Đề xuất cải tiến, 7. Ý kiến phản hồi & Thảo luận của bạn, Plan Review Khoi 5 Amr Dispatch

### Community 133 - "Plan Review Pda Cnc Flow"
Cohesion: 0.25
Nodes (8): 1. Cơ chế hoạt động cốt lõi tại trạm CNC, 2. Sơ đồ kiến trúc & Luồng dữ liệu End-to-End, 3. Sơ đồ trình tự thao tác của Công nhân (Sequence Diagram), 4. Hình minh họa giao diện PDA thực tế (Wireframe 4.2-inch), 5. Bảng ma trận trạng thái Slot, 6. Phân quyền trạm (RBAC) đã cập nhật, Plan Review Pda Cnc Flow, KẾ HOẠCH & ĐÁNH GIÁ LUỒNG GIAO DIỆN PDA VẬN HÀNH CNC (`/pda/cnc`)

### Community 134 - "Production Station And Workshop Partition Architecture"
Cohesion: 0.25
Nodes (8): 1. TỔNG QUAN KIẾN TRÚC & TRIẾT LÝ THIẾT KẾ (ARCHITECTURE OVERVIEW), 2. BẢNG DANH MỤC REST API BACKEND, 3. CHI TIẾT CÁC ENDPOINT, SERVICE & RÀNG BUỘC NGHIỆP VỤ (BACKEND DEEP DIVE), 4. CẤU TRÚC DATABASE MODEL & SCHEMAS, 5. KIẾN TRÚC FRONTEND: COMPONENT, HOOKS, CLIENT & TYPES, 6. MA TRẬN RÀNG BUỘC VÀ QUY TẮC AN TOÀN HỆ THỐNG (RULES MATRIX), 7. HƯỚNG DẪN KIỂM SOÁT & DEBUG CODE CHO LẬP TRÌNH VIÊN, Production Station And Workshop Partition Architecture

### Community 136 - "Todo"
Cohesion: 0.25
Nodes (8): Checkpoint 1: Database Clean & Migration Head, Checkpoint 2: Quản trị Vị trí Hoàn chỉnh, Checkpoint 3: Phân Quyền 1 Khu Vực Hoạt Động Mượt Mà, Danh Sách Công Việc Cần Thực Hiện (Task List), Todo, Phase 1: Gỡ bỏ `default_stage_level` & Chuẩn hóa CSDL, Phase 3: Tái cấu trúc Phân Quyền Người Dùng 1 Khu Vực (User Area Assignment), Phase 4: Kiểm thử Toàn diện & Tự động hóa Trình duyệt

### Community 137 - "Outbound Order Model Module (137)"
Cohesion: 0.48
Nodes (5): _outbound_allocated_quantity(), _outbound_detail_status_expr(), _outbound_order_all_details_status(), _outbound_order_allocation_exists(), _outbound_order_has_detail_status()

### Community 138 - "Docker Compose Module (138)"
Cohesion: 0.29
Nodes (7): command, container_name, env_file, image, restart, volumes, celery-beat

### Community 139 - "Docker Compose Module (139)"
Cohesion: 0.29
Nodes (7): command, container_name, env_file, image, restart, volumes, celery-worker-fleet

### Community 140 - "Docker Compose Module (140)"
Cohesion: 0.29
Nodes (7): command, container_name, env_file, image, restart, volumes, celery-worker-logic

### Community 141 - "Docker Compose Module (141)"
Cohesion: 0.29
Nodes (7): command, container_name, env_file, image, restart, volumes, celery-worker-status

### Community 142 - "Adr 002 Cnc Pda Model Selection And Task Plan"
Cohesion: 0.29
Nodes (7): 1. BỐI CẢNH & VẤN ĐỀ (CONTEXT & PROBLEM), 2. QUYẾT ĐỊNH KIẾN TRÚC (THE ARCHITECTURAL DECISION), 3. DANH SÁCH CÔNG VIỆC CẦN LÀM (TASK TRACKER), 4. HỆ QUẢ & ĐÁNH GIÁ (CONSEQUENCES), 5. CẬP NHẬT TRẠNG THÁI REAL-TIME TỪ KUKA FLEET (QUEUED vs CALLING), Code cũ trong dispatch_core.py:, Adr 002 Cnc Pda Model Selection And Task Plan

### Community 143 - "Explore Khoi 1 Stations And Machines"
Cohesion: 0.29
Nodes (7): 1. MỤC ĐÍCH, KIẾN TRÚC, STACK VÀ ĐIỂM BẮT ĐẦU (PURPOSE & ENTRY POINTS), 2. BẢN ĐỒ CÂY THƯ MỤC CỦA KHỐI 1 (DIRECTORY MAP), 3. LẦN VẾT 1 LUỒNG ĐẠI DIỆN TỪ ĐẦU ĐẾN CUỐI (END-TO-END TRACE), 4. BỐN CÂU HỎI ĐỊNH HƯỚNG SỬA ĐỔI CODE (THE 4 ORIENTATION QUESTIONS), BẢN ĐỒ ĐỊNH HƯỚNG & THẤU HIỂU CODE KHỐI 1: TRẠM MÁY CNC & PHÂN KHU XƯỞNG, Explore Khoi 1 Stations And Machines, 💡 TỔNG KẾT MENTAL MODEL CHO KHỐI 1

### Community 144 - "alloy"
Cohesion: 0.25
Nodes (8): command, container_name, depends_on, image, ports, restart, volumes, alloy

### Community 145 - "Review Khoi 1 Stations And Machines"
Cohesion: 0.29
Nodes (7): 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW), 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 1 (INVOLVED FILES), 🔍 3. CHI TIẾT CÁC LUỒNG THAO TÁC CỤ THỂ, 🗄️ 4. BẢNG ĐỐI CHIẾU CƠ SỞ DỮ LIỆU (DATABASE SCHEMA SPECIFICATION), 🛡️ 5. TIÊU CHÍ KIỂM ĐỊNH CHẤT LƯỢNG KHỐI 1 (QUALITY CHECKLIST), Review Khoi 1 Stations And Machines, TÀI LIỆU TOÀN DIỆN REVIEW KHỐI 1: TRẠM MÁY CNC & PHÂN KHU XƯỞNG

### Community 146 - "Summary Context Skill"
Cohesion: 0.29
Nodes (7): Behavior on Invocation, Context Summary Skill, Summary Context Skill, Guardrails, Output Format, Role, Worked Example (v2 spec, for shape only)

### Community 147 - "prometheus"
Cohesion: 0.25
Nodes (8): command, container_name, extra_hosts, image, ports, restart, volumes, prometheus

### Community 149 - "services"
Cohesion: 0.29
Nodes (6): services, volumes, alloy_data, grafana_data, loki_data, prometheus_data

### Community 150 - "Review Khoi 5 Amr Dispatch And Queue Worker"
Cohesion: 0.33
Nodes (6): 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW), 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 5 (INVOLVED FILES), 🛡️ 4. TỔNG HỢP CÁC ĐIỂM ĐÃ ĐƯỢC CHUẨN HÓA & ĐÁNH GIÁ CHẤT LƯỢNG MÃ NGUỒN, Review Khoi 5 Amr Dispatch And Queue Worker, Tự suy Cấp độ phôi đầu vào (Input Stage Level), Tự suy Model từ RouteStepMachine của máy

### Community 152 - "Understand Code"
Cohesion: 0.33
Nodes (6): 1. Start with purpose, architecture, stack, entry points, 2. Map the directory structure, 3. Trace one representative flow end to end, 4. Identify the core abstractions and where to make changes, Understand Code, Explore code

### Community 153 - "Kuka Core Database Blueprint"
Cohesion: 0.40
Nodes (5): Kuka Core Database Blueprint, PHẦN 1: SƠ ĐỒ QUAN HỆ THỰC THỂ (3NF MERMAID ERD), PHẦN 2: CHI TIẾT TỪNG BẢNG & TỪNG TRƯỜNG (179 CỘT THỰC TẾ), PHẦN 3: LUỒNG BIẾN ĐỔI DỮ LIỆU TRONG DATABASE QUA 5 KỊCH BẢN XƯƠNG SỐNG, PHẦN 4: ĐÁNH GIÁ CHUYÊN SÂU — DATABASE CÒN ĐIỂM NÀO CẦN CẢI THIỆN THÊM KHÔNG?

### Community 155 - "Adr 001 Deprecate Is Active In Production Stations"
Cohesion: 0.40
Nodes (5): 1. BỐI CẢNH (CONTEXT), 2. VẤN ĐỀ PHÁT SINH (THE PROBLEM), 3. QUYẾT ĐỊNH KIẾN TRÚC (THE DECISION), 4. HỆ QUẢ & LỢI ÍCH (CONSEQUENCES), Adr 001 Deprecate Is Active In Production Stations

### Community 156 - "Kuka Core Database Blueprint"
Cohesion: 0.40
Nodes (5): Kuka Core Database Blueprint, PHẦN 1: SƠ ĐỒ QUAN HỆ THỰC THỂ (3NF MERMAID ERD), PHẦN 2: CHI TIẾT TỪNG BẢNG & TỪNG TRƯỜNG (179 CỘT THỰC TẾ), PHẦN 3: LUỒNG BIẾN ĐỔI DỮ LIỆU TRONG DATABASE QUA 5 KỊCH BẢN XƯƠNG SỐNG, PHẦN 4: ĐÁNH GIÁ CHUYÊN SÂU — TỔNG KẾT HỆ THỐNG 21 BẢNG CHUẨN 3NF

### Community 157 - "Kuka Full System Review Plan"
Cohesion: 0.40
Nodes (5): 🗺️ Bản Đồ Lộ Trình 7 Khối Review, CHI TIẾT 7 KHỐI REVIEW TOÀN DIỆN, Kuka Full System Review Plan, Kế Hoạch Review Toàn Diện Hệ Thống KUKA AMR & WMS, 📋 Tiêu Chí Kiểm Soát Chất Lượng Cho Từng Khối (Quality Checklist)

### Community 158 - "Review Khoi 4 Users And Station Rbac"
Cohesion: 0.40
Nodes (5): 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW), 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 4 (INVOLVED FILES), 🔍 3. CHI TIẾT CÁC VIỄN CẢNH VẬN HÀNH (OPERATIONAL SCENARIOS), 🛡️ 4. TỔNG HỢP CÁC ĐIỂM ĐÃ ĐƯỢC CHUẨN HÓA & KHẮC PHỤC TRIỆT ĐỂ, Review Khoi 4 Users And Station Rbac

### Community 159 - "postgres-exporter"
Cohesion: 0.29
Nodes (7): DATA_SOURCE_NAME, container_name, environment, image, ports, restart, postgres-exporter

### Community 161 - "redis-exporter"
Cohesion: 0.29
Nodes (7): REDIS_ADDR, container_name, environment, image, ports, restart, redis-exporter

### Community 163 - "02 Legacy Archived Modules Reference"
Cohesion: 0.50
Nodes (4): 1. TỔNG QUAN 6 MODULE TRONG `backend/legacy_wms_archive/`, 2. GIẢI PHẪU CHI TIẾT TỪNG MODULE & TỪNG HÀM ĐÃ BỎ, 3. BẢNG ĐỐI CHIẾU: CƠ CHẾ LOCK & VẬN CHUYỂN CŨ vs. MỚI, 02 Legacy Archived Modules Reference

### Community 164 - "Readme"
Cohesion: 0.50
Nodes (4): Readme, Expanding the ESLint configuration, React Compiler, React + TypeScript + Vite

### Community 165 - "loki"
Cohesion: 0.29
Nodes (7): command, container_name, image, ports, restart, volumes, loki

### Community 167 - "Plan"
Cohesion: 0.50
Nodes (4): 1. Overview & Locked Decisions, 2. Architecture & Database Design, 3. Task Breakdown by Phases, Plan

### Community 172 - "01 Core Modules And Functions Reference"
Cohesion: 0.67
Nodes (3): 1. SƠ ĐỒ KIẾN TRÚC LÕI HIỆN TẠI (`backend/app/`), 2. GIẢI PHẪU CHI TIẾT MODULE ĐIỀU PHỐI (`backend/app/modules/production/`), 01 Core Modules And Functions Reference

### Community 173 - "Core Database Architecture Specification"
Cohesion: 0.67
Nodes (3): ĐẶC TẢ KIẾN TRÚC CƠ SỞ DỮ LIỆU LÕI KUKA AMR (3NF NORMALIZED SPECIFICATION), Core Database Architecture Specification, Tóm tắt Cấu trúc 22 Bảng Nghiệp vụ (3NF)

### Community 197 - "5. Thiết Lập Mạng Dùng Chung & Cấu Hình Môi Trường (.env)"
Cohesion: 0.67
Nodes (3): 5.1. Tạo mạng Docker dùng chung (External Bridge Network), 5.2. Chuẩn bị file `.env` chuẩn hóa cho Linux Production, 5. Thiết Lập Mạng Dùng Chung & Cấu Hình Môi Trường (.env)

### Community 198 - "database.py"
Cohesion: 0.09
Nodes (14): run_migrations_offline(), run_migrations_online(), FleetApiCall, ProductionRecord, RouteStepMachine, TaskStatus, TransportQueue, UserLocation (+6 more)

## Knowledge Gaps
- **276 isolated node(s):** `masan-wms`, `ADR-0002`, `0. CÁC QUYẾT ĐỊNH ĐÃ CHỐT`, `10. THỨ TỰ THỰC HIỆN & COMMIT`, `1. CẤU HÌNH (`backend/app/core/config.py`)` (+271 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1235 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `root()` connect `root` to `README.md`, `get_redis`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `Location` (e.g. with `get_raw_material_andon_queue()` and `CartSelector`) actually correct?**
  _`Location` has 66 INFERRED edges - model-reasoned connections that need verification._
- **What connects `masan-wms`, `ADR-0002`, `0. CÁC QUYẾT ĐỊNH ĐÃ CHỐT` to the rest of the system?**
  _276 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sqlalchemy` be split into smaller, more focused modules?**
  _Cohesion score 0.020029573867455304 - nodes in this community are weakly interconnected._
- **Why does `react` connect `Frontend UI Components (30)` to `index.tsx`, `Warehouse Domain (2)`, `ItemDetailPage.tsx`, `Warehouse Location & Storage (12)`, `ReportPage.tsx`, `Warehouse Location & Storage (24)`, `StationSettingPage.tsx`, `SkuSearchSelect.tsx`, `useAuth.ts`, `Warehouse Domain (55)`, `ProductionRoutePage.tsx`, `OperatorMapCanvas.tsx`, `dependencies`, `useQrCodePrint.ts`, `package.json`, `useWarehouse.tsx`, `axiosInstance.ts`, `WarehouseMapImportDialog.tsx`, `useAppStore`, `OperatorPageHeader.tsx`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 69 inferred relationships involving `ItemStock` (e.g. with `get_raw_material_andon_queue()` and `CartSelector`) actually correct?**
  _`ItemStock` has 69 INFERRED edges - model-reasoned connections that need verification._
- **Should `index.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.10853658536585366 - nodes in this community are weakly interconnected._