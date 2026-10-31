# Warehouse Domain (36)

> 41 nodes · cohesion 0.13

## Key Concepts

- **item_import_utils.py** (39 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **update_import_job()** (13 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **mark_import_job_failed()** (12 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **Any** (12 connections)
- **item_celery_task.py** (11 connections) — `backend/app/modules/warehouse/item/item_celery_task.py`
- **Session** (10 connections)
- **run_import_item_staging_phase()** (10 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **run_import_item_upsert_phase()** (10 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **get_import_job()** (8 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **save_import_job()** (8 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **_start_import_background()** (8 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **import_item_masan_upsert_task()** (7 connections) — `backend/app/modules/warehouse/item/item_celery_task.py`
- **get_import_file_path()** (7 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **iter_csv_chunks()** (7 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **run_import_item_masan_pipeline()** (7 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **copy_to_staging_table()** (6 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **save_import_item_file()** (6 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **collect_staging_validation_errors()** (5 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **_copy_chunk()** (5 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **Path** (5 connections)
- **upsert_staging_to_item()** (5 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **validate_staging_for_import()** (5 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **_run()** (5 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **ensure_units_from_staging()** (4 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- **import_item_storage_name()** (4 connections) — `backend/app/modules/warehouse/item/item_import_utils.py`
- *... and 16 more nodes in this community*

## Relationships

- [Warehouse Domain (14)](Warehouse_Domain_14.md) (21 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (10 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (5 shared connections)
- [Mock Print Export Module (21)](Mock_Print_Export_Module_21.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Main Module (109)](Main_Module_109.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/item/item_celery_task.py`
- `backend/app/modules/warehouse/item/item_import_utils.py`
- `backend/app/modules/warehouse/item/item_service.py`

## Audit Trail

- EXTRACTED: 147 (99%)
- INFERRED: 2 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*