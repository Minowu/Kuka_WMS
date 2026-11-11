"""Per-request metadata shared by audit/action logs: real client IP, client type,
payload masking. Stored in a ContextVar so services can read it without ``Request``."""
from __future__ import annotations

import contextvars
import ipaddress
import json
from functools import lru_cache
from typing import Any, Optional

from app.core.config import settings

SENSITIVE_KEYS = {
    "password",
    "password_confirm",
    "refresh_token",
    "access_token",
    "token",
    "secret",
    "authorization",
}
MASK = "***"
MAX_PAYLOAD_CHARS = 8000
CLIENT_TYPES = {"pda", "tv", "desktop"}

_request_meta: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "wms_request_meta", default={}
)


@lru_cache(maxsize=1)
def _trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []
    for part in settings.trusted_proxy_cidrs.split(","):
        if part.strip():
            networks.append(ipaddress.ip_network(part.strip(), strict=False))
    return networks


def _is_trusted_proxy(host: Optional[str]) -> bool:
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in net for net in _trusted_proxy_networks())


def get_client_ip(direct_host: Optional[str], headers: dict[str, str]) -> Optional[str]:
    """Real device IP. Proxy headers are only trusted when the TCP peer is our nginx,
    otherwise anyone calling port 8001 directly could spoof X-Forwarded-For."""
    if not _is_trusted_proxy(direct_host):
        return direct_host
    real_ip = headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return direct_host


def build_request_meta(scope: dict[str, Any], headers: dict[str, str], request_id: str) -> dict[str, Any]:
    client_type = (headers.get("x-client-type") or "").strip().lower()
    return {
        "ip": get_client_ip((scope.get("client") or [None])[0], headers),
        "user_agent": (headers.get("user-agent") or "")[:500] or None,
        "client_type": client_type if client_type in CLIENT_TYPES else None,
        "request_id": request_id,
        "method": scope.get("method"),
        "path": scope.get("path"),
    }


def set_request_meta(meta: dict[str, Any]) -> contextvars.Token:
    return _request_meta.set(meta)


def reset_request_meta(token: contextvars.Token) -> None:
    _request_meta.reset(token)


def get_request_meta() -> dict[str, Any]:
    return _request_meta.get()


def mask_payload(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: (MASK if str(k).lower() in SENSITIVE_KEYS else mask_payload(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_payload(v) for v in data]
    return data


def truncate_payload(data: Any) -> Any:
    if data is None:
        return None
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) <= MAX_PAYLOAD_CHARS:
        return data
    return {"_truncated": True, "preview": text[:MAX_PAYLOAD_CHARS]}
