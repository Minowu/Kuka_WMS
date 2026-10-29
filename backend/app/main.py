import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.modules.auth.auth_api import router as auth_router
from app.modules.warehouse.warehouse_zone.warehouse_api import router as warehouse_router
from app.modules.warehouse.location_map.location_api import router as location_router
from app.modules.warehouse.item.item_api import router as item_router
from app.modules.warehouse.item_stock.item_stock_api import router as item_stock_router
from app.modules.warehouse.notificcation.notification_api import router as notification_router
from app.modules.warehouse.dashboard.dashboard_api import router as dashboard_router
from app.modules.production.route_api import router as production_router
from app.core.logger import setup_logger
from app.core.cache import close_redis, get_redis
from app.socket.ws_manager import ws_manager, ws_router
import redis
from prometheus_fastapi_instrumentator import Instrumentator

logger = setup_logger(
    name="main",
    log_level="INFO",
    service_name=settings.app_name,
    log_dir="logs/main"
)

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
    yield
    # stop app
    close_redis()
    logger.info("Stopping app")
    await ws_manager.stop()
    logger.info("Websocket manager stopped")

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
    max_age=3600,
)

Instrumentator().instrument(app).expose(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(location_router, prefix="/api/v1")
app.include_router(item_router, prefix="/api/v1")
app.include_router(item_stock_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(production_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")

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
