"""Utilities for Masan bulk item import (CSV streaming, staging, validate, UPSERT)."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Callable, Iterator

from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.logger import get_logger

logger = get_logger("main")

# backend/app/static/file_import_item — khớp volume Docker ./backend/app/static/file_import_item
IMPORT_ITEM_DIR = Path(__file__).resolve().parents[3] / "static" / "file_import_item"
ALLOWED_IMPORT_EXTENSIONS = {".csv"}


def import_item_storage_name(warehouse_id: int) -> str:
    return f"{warehouse_id}_Masan_Item_data.csv"


def get_import_file_path(warehouse_id: int) -> Path:
    return IMPORT_ITEM_DIR / import_item_storage_name(warehouse_id)
CHUNK_SIZE = 50_000
MAX_IMPORT_ERRORS = 50
DEFAULT_IMPORT_MIN_QUANTITY = 10
DEFAULT_IMPORT_MAX_QUANTITY = 999_999
IMPORT_JOB_REDIS_TTL = 3600

HEADER_MASAN_CSV = {
    "Item No": "sku",
    "Item Name": "name",
    "UOM1": "base_unit",
    "UOM Conversion / Pallet": "base_quantity",
}

STAGING_FIELDS = (
    "sku",
    "name",
    "description",
    "supplier",
    "base_unit",
    "base_quantity",
    "min_quantity",
    "max_quantity",
)

_INTEGER_IMPORT_FIELDS = frozenset({"base_quantity", "min_quantity", "max_quantity"})


def normalize_import_integer(value: str) -> str:
    """Remove thousands separators so values like '1,400' parse as 1400."""
    cleaned = value.strip()
    if not cleaned:
        return ""
    return cleaned.replace(",", "")


def normalize_base_quantity(value: str) -> str:
    """Normalize pallet conversion; Masan uses 0 when not applicable → treat as 1."""
    normalized = normalize_import_integer(value)
    if normalized == "0":
        return "1"
    return normalized

_STAGING_VALIDATION_SQL = text("""
    WITH staging AS (
        SELECT
            row_no,
            btrim(sku) AS sku,
            btrim(name) AS name,
            btrim(base_unit) AS base_unit,
            btrim(base_quantity) AS base_quantity
        FROM item_import_staging
        WHERE job_id = CAST(:job_id AS uuid)
    ),
    errors AS (
        SELECT row_no, sku, 'SKU không được để trống' AS message
        FROM staging WHERE sku = ''
        UNION ALL
        SELECT row_no, sku, 'Tên sản phẩm không được để trống'
        FROM staging WHERE name = ''
        UNION ALL
        SELECT row_no, sku, 'Đơn vị không được để trống'
        FROM staging WHERE base_unit = ''
        UNION ALL
        SELECT row_no, sku, 'SKU vượt quá 50 ký tự'
        FROM staging WHERE length(sku) > 50
        UNION ALL
        SELECT row_no, sku, 'Tên vượt quá 255 ký tự'
        FROM staging WHERE length(name) > 255
        UNION ALL
        SELECT row_no, sku, 'base_quantity phải là số nguyên >= 1'
        FROM staging
        WHERE base_quantity <> ''
          AND (base_quantity !~ '^[0-9]+$' OR base_quantity::bigint < 1)
        UNION ALL
        SELECT MIN(row_no), sku, 'SKU trùng lặp trong file'
        FROM staging
        WHERE sku <> ''
        GROUP BY sku
        HAVING COUNT(*) > 1
    )
    SELECT row_no, sku, message
    FROM errors
    ORDER BY row_no
    LIMIT :limit
""")


def import_job_redis_key(job_id: str) -> str:
    return f"item:import:job:{job_id}"


def new_import_job_payload(
    job_id: str,
    warehouse_id: int,
    filename: str,
    *,
    status: str = "pending",
    message: str = "Đang chờ xử lý",
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "status": status,
        "warehouse_id": warehouse_id,
        "filename": filename,
        "processed": 0,
        "total": 0,
        "created": 0,
        "updated": 0,
        "error_count": 0,
        "errors": [],
        "message": message,
    }


def save_import_job(job_id: str, payload: dict[str, Any]) -> None:
    cache_set(import_job_redis_key(job_id), payload, ttl=IMPORT_JOB_REDIS_TTL)


def get_import_job(job_id: str) -> dict[str, Any] | None:
    return cache_get(import_job_redis_key(job_id))


def update_import_job(job_id: str, **fields: Any) -> dict[str, Any]:
    payload = get_import_job(job_id) or {"job_id": job_id}
    payload.update(fields)
    save_import_job(job_id, payload)
    return payload


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    lines = [
        f"Dòng {e['row_no']} (SKU: {e['sku'] or '-'}): {e['message']}"
        for e in errors[:MAX_IMPORT_ERRORS]
    ]
    if len(errors) > MAX_IMPORT_ERRORS:
        lines.append(f"... và {len(errors) - MAX_IMPORT_ERRORS} lỗi khác")
    return "\n".join(lines)


def validation_errors_for_response(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"row": e["row_no"], "sku": e["sku"] or "", "message": e["message"]}
        for e in errors[:MAX_IMPORT_ERRORS]
    ]


async def save_import_item_file(file: UploadFile, warehouse_id: int) -> tuple[str, int, Path]:
    if not file.filename:
        raise ValueError("File name is invalid")

    filename = file.filename
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMPORT_EXTENSIONS:
        raise ValueError("Only support file .csv")

    dest = get_import_file_path(warehouse_id)
    dest.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(8 * 1024 * 1024):
            size += len(chunk)
            out.write(chunk)

    await file.close()

    if size == 0:
        dest.unlink(missing_ok=True)
        raise ValueError("File is empty")

    return filename, size, dest


def iter_csv_chunks(path: Path, chunk_size: int = CHUNK_SIZE) -> Iterator[list[dict[str, Any]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        next(handle, None)
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise ValueError("CSV không có header")

        normalized_headers = {
            (name or "").strip(): name for name in reader.fieldnames
        }

        missing = [src for src in HEADER_MASAN_CSV if src not in normalized_headers]
        if missing:
            raise ValueError(f"Thiếu cột bắt buộc: {', '.join(missing)}")

        chunk: list[dict[str, Any]] = []

        for row_no, raw in enumerate(reader, start=3):
            row: dict[str, Any] = {"row_no": row_no}

            for src, dst in HEADER_MASAN_CSV.items():
                original_key = normalized_headers[src]
                value = raw.get(original_key)
                row[dst] = "" if value is None else str(value).strip()

            for field in STAGING_FIELDS:
                row.setdefault(field, "")

            for field in _INTEGER_IMPORT_FIELDS:
                if field == "base_quantity":
                    row[field] = normalize_base_quantity(row[field])
                else:
                    row[field] = normalize_import_integer(row[field])

            if not row["sku"] and not row["name"]:
                continue

            chunk.append(row)

            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

        if chunk:
            yield chunk


def _copy_chunk(cur, job_id: str, rows: list[dict[str, Any]]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow([
            job_id,
            row.get("row_no", ""),
            row.get("sku", ""),
            row.get("name", ""),
            row.get("description", ""),
            row.get("supplier", ""),
            row.get("base_unit", ""),
            row.get("base_quantity", ""),
            row.get("min_quantity", ""),
            row.get("max_quantity", ""),
        ])
    buf.seek(0)

    cur.copy_expert(
        """
        COPY item_import_staging (
            job_id, row_no, sku, name, description, supplier,
            base_unit, base_quantity, min_quantity, max_quantity
        )
        FROM STDIN WITH (FORMAT csv, NULL '')
        """,
        buf,
    )


def copy_to_staging_table(
    db: Session,
    file_path: str,
    job_id: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    on_progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise ValueError("File not found")
    if path.suffix.lower() != ".csv":
        raise ValueError("Only CSV is supported")

    raw_conn = db.connection().connection
    processed = 0

    try:
        with raw_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM item_import_staging WHERE job_id = CAST(%s AS uuid)",
                (job_id,),
            )
            for chunk in iter_csv_chunks(path, chunk_size):
                _copy_chunk(cur, job_id, chunk)
                processed += len(chunk)
                if on_progress:
                    on_progress(processed)

            if processed == 0:
                raise ValueError("File không có dòng dữ liệu")

        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise

    return {
        "processed": processed,
        "total_rows": processed,
    }


def delete_staging_for_job(db: Session, job_id: str) -> None:
    raw_conn = db.connection().connection
    with raw_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM item_import_staging WHERE job_id = CAST(%s AS uuid)",
            (job_id,),
        )
    raw_conn.commit()


def collect_staging_validation_errors(
    db: Session,
    job_id: str,
    limit: int = MAX_IMPORT_ERRORS,
) -> list[dict[str, Any]]:
    rows = db.execute(
        _STAGING_VALIDATION_SQL,
        {"job_id": job_id, "limit": limit + 1},
    ).mappings().all()
    return [dict(r) for r in rows]


def validate_staging_for_import(db: Session, job_id: str) -> None:
    errors = collect_staging_validation_errors(db, job_id)
    if errors:
        raise ValueError(format_validation_errors(errors))


_MASAN_UNIT_DESCRIPTION = "Tạo tự động từ import Masan"


def ensure_units_from_staging(db: Session, job_id: str) -> int:
    """Insert missing units referenced in staging (case-insensitive match on name)."""
    result = db.execute(
        text(
            """
            INSERT INTO unit (name, description)
            SELECT unit_name, :description
            FROM (
                SELECT lower(btrim(base_unit)) AS unit_key,
                       min(btrim(base_unit)) AS unit_name
                FROM item_import_staging
                WHERE job_id = CAST(:job_id AS uuid)
                  AND btrim(base_unit) <> ''
                GROUP BY lower(btrim(base_unit))
            ) AS candidates
            WHERE NOT EXISTS (
                SELECT 1 FROM unit u WHERE lower(u.name) = candidates.unit_key
            )
            """
        ),
        {"job_id": job_id, "description": _MASAN_UNIT_DESCRIPTION},
    )
    db.commit()
    return int(result.rowcount or 0)


def upsert_staging_to_item(db: Session, job_id: str, warehouse_id: int) -> dict[str, int]:
    units_created = ensure_units_from_staging(db, job_id)
    validate_staging_for_import(db, job_id)

    raw_conn = db.connection().connection
    try:
        with raw_conn.cursor() as cur:
            cur.execute(
                """
                WITH upserted AS (
                    INSERT INTO item (
                        sku, name, base_unit,
                        warehouse_id, supplier, description, details, is_active
                    )
                    SELECT
                        btrim(s.sku),
                        btrim(s.name),
                        u.id,
                        %s,
                        COALESCE(NULLIF(btrim(s.supplier), ''), ''),
                        NULLIF(btrim(s.description), ''),
                        '{}'::jsonb,
                        true
                    FROM item_import_staging s
                    INNER JOIN unit u ON lower(u.name) = lower(btrim(s.base_unit))
                    WHERE s.job_id = CAST(%s AS uuid)
                    ON CONFLICT (sku) DO UPDATE SET
                        name = EXCLUDED.name,
                        base_unit = EXCLUDED.base_unit,
                        warehouse_id = EXCLUDED.warehouse_id,
                        updated_at = NOW()
                    RETURNING (xmax = 0) AS inserted
                )
                SELECT
                    COUNT(*) FILTER (WHERE inserted) AS created,
                    COUNT(*) FILTER (WHERE NOT inserted) AS updated
                FROM upserted
                """,
                (
                    warehouse_id,
                    job_id,
                ),
            )
            created, updated = cur.fetchone()
            cur.execute(
                "DELETE FROM item_import_staging WHERE job_id = CAST(%s AS uuid)",
                (job_id,),
            )
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise

    created_count = int(created or 0)
    updated_count = int(updated or 0)
    return {
        "created": created_count,
        "updated": updated_count,
        "upserted": created_count + updated_count,
        "units_created": units_created,
    }


def run_import_item_staging_phase(
    db: Session,
    job_id: str,
    warehouse_id: int,
    file_path: Path,
) -> int:
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    def on_copy_progress(processed: int) -> None:
        update_import_job(
            job_id,
            status="running",
            warehouse_id=warehouse_id,
            processed=processed,
            total=processed,
            message=f"Đang copy staging: {processed:,} dòng",
        )

    update_import_job(
        job_id,
        status="running",
        warehouse_id=warehouse_id,
        message="Đang copy dữ liệu vào staging",
    )

    staging = copy_to_staging_table(
        db,
        str(file_path),
        job_id,
        on_progress=on_copy_progress,
    )
    processed = staging["processed"]
    
    # Auto-create any missing units from the staging data before validation
    auto_create_missing_units(db, job_id)

    update_import_job(
        job_id,
        status="running",
        warehouse_id=warehouse_id,
        processed=processed,
        total=processed,
        message=f"Đang chờ import {processed:,} dòng vào hệ thống",
    )
    return processed


def run_import_item_upsert_phase(
    db: Session,
    job_id: str,
    warehouse_id: int,
    filename: str,
    *,
    processed: int | None = None,
) -> dict[str, Any]:
    job = get_import_job(job_id) or {}
    row_count = processed if processed is not None else int(job.get("processed") or 0)

    update_import_job(
        job_id,
        status="running",
        warehouse_id=warehouse_id,
        filename=filename,
        processed=row_count,
        total=row_count,
        message=f"Đang validate và import {row_count:,} dòng",
    )

    promote = upsert_staging_to_item(db, job_id, warehouse_id)
    units_created = int(promote.get("units_created") or 0)

    summary = (
        f"Import xong: {promote['created']:,} mới, "
        f"{promote['updated']:,} cập nhật"
    )
    if units_created:
        summary += f", {units_created:,} đơn vị mới"

    result = {
        "job_id": job_id,
        "status": "completed",
        "warehouse_id": warehouse_id,
        "filename": filename,
        "processed": row_count,
        "total": row_count,
        "created": promote["created"],
        "updated": promote["updated"],
        "error_count": 0,
        "errors": [],
        "message": summary,
    }
    save_import_job(job_id, result)
    logger.info(
        "item import completed job_id=%s warehouse_id=%s processed=%s created=%s updated=%s units_created=%s",
        job_id,
        warehouse_id,
        row_count,
        promote["created"],
        promote["updated"],
        units_created,
    )
    return result


def run_import_item_masan_pipeline(
    db: Session,
    job_id: str,
    warehouse_id: int,
    filename: str,
    *,
    file_path: Path | None = None,
) -> dict[str, Any]:
    resolved_path = file_path or get_import_file_path(warehouse_id)
    processed = run_import_item_staging_phase(
        db,
        job_id,
        warehouse_id,
        resolved_path,
    )
    return run_import_item_upsert_phase(
        db,
        job_id,
        warehouse_id,
        filename,
        processed=processed,
    )


def mark_import_job_failed(
    db: Session,
    job_id: str,
    exc: Exception,
    *,
    warehouse_id: int | None = None,
    filename: str | None = None,
) -> None:
    errors = collect_staging_validation_errors(db, job_id)
    try:
        delete_staging_for_job(db, job_id)
    except Exception:
        logger.exception("item import failed to cleanup staging job_id=%s", job_id)

    message = str(exc)
    update_import_job(
        job_id,
        status="failed",
        warehouse_id=warehouse_id,
        filename=filename,
        error_count=len(errors) if errors else 1,
        errors=validation_errors_for_response(errors) if errors else [],
        message=message,
    )
    logger.error("item import failed job_id=%s error=%s", job_id, message)
