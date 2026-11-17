import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.adapters.api.v1.auth import auth_router
from app.adapters.api.v1.production import production_router, rack_router, request_router
from app.adapters.api.v1.warehouse import (
    dashboard_router,
    item_router,
    item_stock_router,
    location_router,
    notification_router,
    warehouse_router,
)
from app.core.logger import configure_logging, get_logger
from app.core.cache import close_redis, get_redis
from app.socket.ws_manager import ws_manager, ws_router
from app.core.observability import RequestLoggingMiddleware, install_exception_handlers
from app.modules.client_logs.client_logs_api import router as client_logs_router
from app.modules.audit.audit_api import router as audit_router
import redis
from prometheus_fastapi_instrumentator import Instrumentator

configure_logging()
logger = get_logger("wms.system")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # start app
    logger.info("Starting app")
    try:
        get_redis().ping()
        logger.info(
            "Redis connected: %s (prefix=%s)",
            settings.redis_url,
            settings.redis_key_prefix,
        )

        await ws_manager.start()
        logger.info("Websocket manager started")
    except redis.RedisError as e:
        logger.error("Redis connection failed: %s", e)
        raise RuntimeError("Cannot connect to Redis") from e
    try:
        yield
    finally:
        try:
            close_redis()
            logger.info("Stopping app")
            await ws_manager.stop()
            logger.info("Websocket manager stopped")
        except Exception as e:
            logger.warning("Error during lifespan shutdown: %s", e)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FE development URL
    allow_credentials=False,
    allow_methods=["*"],   # allow all methods
    allow_headers=["*"],   # allow all headers
    expose_headers=["X-Request-ID"],
    max_age=3600,
)

app.add_middleware(RequestLoggingMiddleware)
install_exception_handlers(app)

Instrumentator().instrument(app).expose(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(location_router, prefix="/api/v1")
app.include_router(item_router, prefix="/api/v1")
app.include_router(item_stock_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(production_router, prefix="/api/v1")
app.include_router(rack_router, prefix="/api/v1")
app.include_router(request_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(client_logs_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Thado Warehouse Management System API",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
