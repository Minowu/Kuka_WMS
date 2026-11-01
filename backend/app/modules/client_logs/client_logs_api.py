"""POST /api/v1/logs/client — frontend/PDA log ingestion into channel wms.frontend."""
from __future__ import annotations

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.modules.auth.auth_model import User

router = APIRouter(tags=["Logs"])
frontend_log = get_logger("wms.frontend")

_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING,
           "warning": logging.WARNING, "error": logging.ERROR, "critical": logging.CRITICAL}


class ClientLogEntry(BaseModel):
    ts: Optional[str] = None
    level: str = "info"
    msg: str
    context: dict[str, Any] = Field(default_factory=dict)


class ClientLogBatch(BaseModel):
    entries: list[ClientLogEntry] = Field(..., max_length=100)


@router.post("/logs/client")
def ingest_client_logs(
    batch: ClientLogBatch,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    for e in batch.entries:
        frontend_log.log(
            _LEVELS.get(e.level.lower(), logging.INFO),
            e.msg,
            extra={"client_ts": e.ts, "client_context": e.context, "user": user.username},
        )
    return {"accepted": len(batch.entries)}
