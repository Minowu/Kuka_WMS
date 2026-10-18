from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.config import settings
from app.core.database import Base

# Import all active core models to register metadata
from app.modules.auth.auth_model import (  # noqa: F401
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserWarehouse,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse  # noqa: F401
from app.modules.warehouse.location_map.location_model import Location, WarehouseMap  # noqa: F401
from app.modules.warehouse.item.item_model import Item  # noqa: F401
from app.modules.warehouse.item_stock.item_stock_model import ItemStock  # noqa: F401
from app.modules.warehouse.notificcation.notification_model import Notification  # noqa: F401
from app.modules.production.production_models import (  # noqa: F401
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TaskStatus,
    TransportQueue,
    TransportRequest,
    UserLocation,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
