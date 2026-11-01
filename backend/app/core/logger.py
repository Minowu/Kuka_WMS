"""Centralised logging for KUKA_WMS.

Channels are named loggers under ``wms.*`` (see vault-docs/logging-conventions.md).
Outputs:
  - console: readable, colored text
  - logs/all.jsonl      : every record (JSON lines)
  - logs/error.jsonl    : WARNING and above
  - logs/{process}.jsonl: per process (api / celery-<queue> / beat)
Context fields (correlation_id, user, station_code, ...) are carried by
contextvars and injected into every record by ``ContextFilter``.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import logging.config
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union

LogDir = Union[str, Path]

CONTEXT_FIELDS = (
    "correlation_id",
    "user",
    "station_code",
    "machine_code",
    "container_code",
    "transport_request_id",
    "fleet_task_id",
    "fleet_request_id",
    "duration_ms",
)

_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
DEFAULT_LOG_DIR = Path(os.getenv("WMS_LOG_DIR", str(_BASE_DIR / "logs")))

# Immutable-style context (each log_context creates a new dict).
_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("wms_log_context", default={})
# Mutable per-request scope: lets code running in a copied context (e.g. FastAPI
# sync dependencies in a threadpool) publish values back to the request owner.
_scope: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar("wms_log_scope", default=None)

_configured = False


# --------------------------------------------------------------------------- context
def get_context() -> dict[str, Any]:
    merged = dict(_scope.get() or {})
    merged.update(_context.get())
    return merged


def bind_context(**fields: Any) -> contextvars.Token:
    """Bind fields for the rest of the current context. Returns a reset token."""
    new = dict(_context.get())
    new.update({k: v for k, v in fields.items() if v is not None})
    scope = _scope.get()
    if scope is not None:
        scope.update({k: v for k, v in fields.items() if v is not None})
    return _context.set(new)


def clear_context(token: Optional[contextvars.Token] = None) -> None:
    if token is not None:
        _context.reset(token)
    else:
        _context.set({})


@contextlib.contextmanager
def log_context(**fields: Any) -> Iterator[dict[str, Any]]:
    """Temporarily bind context fields: ``with log_context(station_code="S1"): ...``"""
    new = dict(_context.get())
    new.update({k: v for k, v in fields.items() if v is not None})
    token = _context.set(new)
    try:
        yield new
    finally:
        _context.reset(token)


@contextlib.contextmanager
def request_scope(**fields: Any) -> Iterator[dict[str, Any]]:
    """Open a mutable scope (used by HTTP middleware / Celery prerun)."""
    scope = {k: v for k, v in fields.items() if v is not None}
    t1 = _scope.set(scope)
    t2 = _context.set(dict(scope))
    try:
        yield scope
    finally:
        _context.reset(t2)
        _scope.reset(t1)


# --------------------------------------------------------------------------- process
def detect_process() -> str:
    env = os.getenv("WMS_PROCESS")
    if env:
        return env
    argv = " ".join(sys.argv).lower()
    if "celery" in argv:
        if " beat" in argv:
            return "beat"
        queue = None
        for i, a in enumerate(sys.argv):
            if a in ("-Q", "--queues") and i + 1 < len(sys.argv):
                queue = sys.argv[i + 1]
            elif a.startswith("--queues=") or (a.startswith("-Q") and len(a) > 2):
                queue = a.split("=", 1)[-1] if "=" in a else a[2:]
        return f"celery-{queue.replace(',', '-')}" if queue else "celery"
    if "pytest" in argv:
        return "test"
    return "api"


# --------------------------------------------------------------------------- filter / formatters
class ContextFilter(logging.Filter):
    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.process_name = detect_process()

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_context()
        for f in CONTEXT_FIELDS:
            if not hasattr(record, f):
                setattr(record, f, ctx.get(f))
        for k, v in ctx.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        if not hasattr(record, "process_name"):
            record.process_name = self.process_name
        return True


_STD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message", "asctime", "process_name", "taskName", *CONTEXT_FIELDS,
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "channel": record.name,
            "process": getattr(record, "process_name", None) or detect_process(),
            "pid": record.process,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "msg": record.getMessage(),
        }
        ctx = get_context()
        for f in CONTEXT_FIELDS:
            v = getattr(record, f, None)
            if v is None:
                v = ctx.get(f)
            if v is not None:
                data[f] = v
        for k, v in ctx.items():
            if v is not None and k not in data:
                data[k] = v
        for k, v in record.__dict__.items():
            if k not in _STD_ATTRS and not k.startswith("_"):
                data[k] = v
        if record.exc_info:
            data["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            data["stack"] = "".join(traceback.format_exception(*record.exc_info))
        elif record.stack_info:
            data["stack"] = record.stack_info
        return json.dumps(data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    COLORS = {"DEBUG": "\033[36m", "INFO": "\033[32m", "WARNING": "\033[33m", "ERROR": "\033[31m", "CRITICAL": "\033[41m"}
    RESET = "\033[0m"

    def __init__(self, use_color: Optional[bool] = None) -> None:
        super().__init__(datefmt="%H:%M:%S")
        self.use_color = sys.stdout.isatty() if use_color is None else use_color

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, self.datefmt)
        lvl = record.levelname
        if self.use_color:
            lvl = f"{self.COLORS.get(lvl, '')}{lvl:<8}{self.RESET}"
        else:
            lvl = f"{lvl:<8}"
        ctx = " ".join(
            f"{f}={getattr(record, f)}" for f in CONTEXT_FIELDS if getattr(record, f, None) is not None
        )
        line = f"{ts} {lvl} [{record.name}] {record.getMessage()}"
        if ctx:
            line += f"  ({ctx})"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


# --------------------------------------------------------------------------- configuration
def _channel_overrides() -> dict[str, dict[str, Any]]:
    """LOG_LEVEL_WMS_FLEET_OUT=INFO -> logger 'wms.fleet.out'; LOG_LEVEL_SQLALCHEMY=INFO -> 'sqlalchemy'."""
    out: dict[str, dict[str, Any]] = {}
    for key, val in os.environ.items():
        if key.startswith("LOG_LEVEL_") and key != "LOG_LEVEL_":
            name = key[len("LOG_LEVEL_"):].lower().replace("__", "-").replace("_", ".")
            out[name] = {"level": val.upper()}
    return out


def configure_logging(log_dir: Optional[LogDir] = None, process: Optional[str] = None, force: bool = False) -> None:
    """Idempotent global logging setup via dictConfig."""
    global _configured
    if process:
        os.environ["WMS_PROCESS"] = process
        force = True
    if _configured and not force:
        return
    proc = detect_process()
    path = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    path.mkdir(parents=True, exist_ok=True)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(50 * 1024 * 1024)))
    backups = int(os.getenv("LOG_BACKUP_COUNT", "20"))

    def file_handler(fname: str, level: str = "DEBUG") -> dict[str, Any]:
        return {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(path / fname),
            "maxBytes": max_bytes,
            "backupCount": backups,
            "encoding": "utf-8",
            "delay": True,
            "level": level,
            "formatter": "json",
            "filters": ["context"],
        }

    handlers_all = ["console", "all", "error", "process"]
    loggers: dict[str, dict[str, Any]] = {
        "wms": {"level": os.getenv("LOG_LEVEL_WMS", "DEBUG"), "handlers": handlers_all, "propagate": False},
        # legacy channel name used by old callers
        "main": {"level": "DEBUG", "handlers": handlers_all, "propagate": False},
        "uvicorn": {"level": "INFO"},
        "uvicorn.access": {"level": "WARNING"},
        "sqlalchemy": {"level": "WARNING"},
        "sqlalchemy.engine": {"level": "WARNING"},
        "celery": {"level": "INFO"},
        "kombu": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "urllib3": {"level": "WARNING"},
        "asyncio": {"level": "WARNING"},
        "multipart": {"level": "WARNING"},
    }
    for name, cfg in _channel_overrides().items():
        loggers.setdefault(name, {}).update(cfg)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"context": {"()": ContextFilter}},
        "formatters": {
            "json": {"()": JsonFormatter},
            "console": {"()": ConsoleFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": os.getenv("LOG_CONSOLE_LEVEL", "DEBUG"),
                "formatter": "console",
                "filters": ["context"],
            },
            "all": file_handler("all.jsonl"),
            "error": file_handler("error.jsonl", "WARNING"),
            "process": file_handler(f"{proc}.jsonl"),
        },
        "loggers": loggers,
        "root": {"level": "INFO", "handlers": handlers_all},
    })
    _configured = True


def setup_logger(
    name: str = "wms",
    log_level: str = "INFO",
    service_name: Optional[str] = None,
    log_dir: LogDir = "logs",
) -> logging.Logger:
    """Backward compatible: ensures global config, returns the named logger.

    ``log_level``/``service_name``/``log_dir`` are kept for API compatibility;
    output location is governed by ``configure_logging``.
    """
    configure_logging()
    return logging.getLogger(name)


def get_logger(name: str = "wms") -> logging.Logger:
    """Return a channel logger, e.g. ``get_logger("wms.dispatch")``."""
    return logging.getLogger(name)
