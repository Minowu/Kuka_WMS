"""Automatic signal capture: HTTP middleware, exception handlers, Celery signals,
SQLAlchemy events. Channels: wms.http, wms.celery.*, wms.db, wms.redis."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.core.logger import bind_context, get_context, get_logger, request_scope

http_log = get_logger("wms.http")
db_log = get_logger("wms.db")
SLOW_QUERY_MS = 200


# --------------------------------------------------------------------------- HTTP
def _decode(body: bytes) -> Any:
    if not body:
        return None
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary {len(body)} bytes>"
    try:
        return json.loads(text)
    except ValueError:
        return text


class RequestLoggingMiddleware:
    """Pure ASGI middleware (keeps streaming/websocket intact)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        rid = headers.get("x-request-id") or uuid.uuid4().hex
        path = scope.get("path", "")
        if path in ("/metrics", "/health"):
            await self.app(scope, receive, send)
            return
        chunks: list[bytes] = []
        resp_chunks: list[bytes] = []
        status = {"code": 500}
        start = time.perf_counter()

        async def recv():
            msg = await receive()
            if msg["type"] == "http.request":
                chunks.append(msg.get("body", b""))
            return msg

        async def snd(msg):
            if msg["type"] == "http.response.start":
                status["code"] = msg["status"]
                hdrs = list(msg.get("headers", []))
                existing = [k.lower() for k, _ in hdrs]
                if b"x-request-id" not in existing:
                    hdrs.append((b"x-request-id", rid.encode()))
                msg["headers"] = hdrs
            elif msg["type"] == "http.response.body" and status["code"] >= 400:
                resp_chunks.append(msg.get("body", b""))
            await send(msg)

        with request_scope(correlation_id=rid) as rscope:
            try:
                await self.app(scope, recv, snd)
            finally:
                dur = round((time.perf_counter() - start) * 1000, 2)
                code = status["code"]
                level = 40 if code >= 500 else 30 if code >= 400 else 20
                http_log.log(
                    level,
                    "%s %s -> %s (%.1f ms)", scope.get("method"), path, code, dur,
                    extra={
                        "method": scope.get("method"),
                        "path": path,
                        "query": scope.get("query_string", b"").decode("latin-1"),
                        "req_body": _decode(b"".join(chunks)),
                        "resp_body": _decode(b"".join(resp_chunks)) if resp_chunks else None,
                        "status": code,
                        "duration_ms": dur,
                        "client": (scope.get("client") or [None])[0],
                        "user": rscope.get("user"),
                    },
                )


def install_exception_handlers(app) -> None:
    from fastapi import HTTPException, Request
    from fastapi.exception_handlers import http_exception_handler
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    async def _http_exc(request: Request, exc: StarletteHTTPException):
        lvl = 40 if exc.status_code >= 500 else 30
        http_log.log(
            lvl,
            "HTTPException %s on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
            exc_info=exc,
            extra={"status": exc.status_code},
        )
        return await http_exception_handler(request, exc)

    async def _value_err(request: Request, exc: ValueError):
        http_log.warning(
            "Unhandled ValueError on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=exc,
            extra={"status": 400},
        )
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    async def _any(request: Request, exc: Exception):
        http_log.error(
            "Unhandled %s on %s %s: %s",
            type(exc).__name__,
            request.method,
            request.url.path,
            exc,
            exc_info=exc,
            extra={"status": 500},
        )
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    app.add_exception_handler(StarletteHTTPException, _http_exc)
    app.add_exception_handler(HTTPException, _http_exc)
    app.add_exception_handler(ValueError, _value_err)
    app.add_exception_handler(Exception, _any)


# --------------------------------------------------------------------------- SQLAlchemy
def install_db_events(engine) -> None:
    from sqlalchemy import event

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_wms_t", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.get("_wms_t")
        if not stack:
            return
        dur = (time.perf_counter() - stack.pop()) * 1000
        if dur > SLOW_QUERY_MS:
            db_log.warning(
                "Slow query %.1f ms: %s",
                dur,
                statement[:2000],
                extra={"duration_ms": round(dur, 2), "params": str(parameters)[:2000]},
            )

    @event.listens_for(engine, "handle_error")
    def _err(ctx):
        conn = ctx.connection
        stack = conn.info.get("_wms_t") if conn else None
        if stack:
            stack.pop()
        db_log.error("DB error: %s | %s", ctx.original_exception, (ctx.statement or "")[:2000])

    @event.listens_for(engine, "rollback")
    def _rollback(conn):
        db_log.info("Transaction rollback")

    @event.listens_for(engine, "checkout")
    def _checkout(dbapi_conn, conn_record, conn_proxy):
        pool = engine.pool
        try:
            if pool.overflow() > 0:
                db_log.warning("Pool overflow in use: %s", pool.status())
        except Exception:  # pool impl without overflow()
            pass


# --------------------------------------------------------------------------- Celery
_celery_scopes: dict[str, Any] = {}
_celery_signals_installed = False


def install_celery_signals() -> None:
    global _celery_signals_installed
    if _celery_signals_installed:
        return
    _celery_signals_installed = True
    from celery import signals

    @signals.setup_logging.connect(weak=False)
    def _setup_logging(**_kw):  # prevents Celery from hijacking the root logger
        from app.core.logger import configure_logging
        configure_logging(force=True)

    @signals.before_task_publish.connect(weak=False)
    def _before_publish(headers=None, **_kw):
        cid = get_context().get("correlation_id")
        if headers is not None and cid:
            headers.setdefault("correlation_id", cid)

    def _chan(task) -> Any:
        queue = None
        try:
            req = getattr(task, "request", None)
            if req:
                queue = (getattr(req, "delivery_info", None) or {}).get("routing_key")
        except Exception:
            pass
        return get_logger(f"wms.celery.{queue or 'unknown'}")

    @signals.task_prerun.connect(weak=False)
    def _prerun(task_id=None, task=None, args=None, kwargs=None, **_kw):
        req = getattr(task, "request", None)
        cid = getattr(req, "correlation_id", None) or (getattr(req, "headers", None) or {}).get("correlation_id")
        cm = request_scope(correlation_id=cid or task_id)
        cm.__enter__()
        _celery_scopes[task_id] = (cm, time.perf_counter())
        bind_context(celery_task_id=task_id)
        _chan(task).info(
            "Task start %s", getattr(task, "name", "?"),
            extra={"task_id": task_id, "args": str(args)[:2000],
                   "kwargs": str(kwargs)[:2000],
                   "worker": getattr(req, "hostname", None) if req else None},
        )

    @signals.task_postrun.connect(weak=False)
    def _postrun(task_id=None, task=None, state=None, **_kw):
        cm, start = _celery_scopes.pop(task_id, (None, None))
        dur = round((time.perf_counter() - start) * 1000, 2) if start else None
        _chan(task).info(
            "Task end %s state=%s (%s ms)", getattr(task, "name", "?"), state, dur,
            extra={"task_id": task_id, "state": state, "duration_ms": dur},
        )
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass

    @signals.task_failure.connect(weak=False)
    def _failure(task_id=None, exception=None, einfo=None, sender=None, **_kw):
        exc_info = (type(exception), exception, exception.__traceback__) if exception else None
        _chan(sender).error(
            "Task failed %s: %s", getattr(sender, "name", "?"), exception,
            exc_info=exc_info, extra={"task_id": task_id},
        )

    @signals.task_retry.connect(weak=False)
    def _retry(request=None, reason=None, sender=None, **_kw):
        _chan(sender).warning(
            "Task retry %s: %s", getattr(sender, "name", "?"), reason,
            extra={"task_id": getattr(request, "id", None),
                   "retries": getattr(request, "retries", None)},
        )

    @signals.beat_init.connect(weak=False)
    def _beat_init(**_kw):
        get_logger("wms.celery.beat").info("Beat started")
