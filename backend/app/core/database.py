import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.config import settings

# Phân định cấu hình Connection Pool theo vai trò (Backend API vs Celery Workers)
# - Celery Worker: Mỗi process prefork tự khởi tạo engine riêng. Với 10 processes,
#   pool_size=2, max_overflow=2 khống chế trần Celery <= 40 connections.
# - Backend API: Phục vụ 40+ PDA đồng thời với pool_size=20, max_overflow=20.
# Tổng ngân sách: 40 + 40 = 80 < max_connections (100-150) của PostgreSQL.
_role = os.getenv("WMS_DB_ROLE", getattr(settings, "db_role", "backend")).lower()
if _role in ("celery", "worker"):
    _pool_size = 2
    _max_overflow = 2
    _pool_timeout = 15
    _pool_recycle = 1800
else:
    _pool_size = getattr(settings, "db_pool_size", 20)
    _max_overflow = getattr(settings, "db_max_overflow", 20)
    _pool_timeout = getattr(settings, "db_pool_timeout", 10)
    _pool_recycle = getattr(settings, "db_pool_recycle", 1800)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=_pool_timeout,
    pool_recycle=_pool_recycle,
)

from app.core.observability import install_db_events  # noqa: E402

install_db_events(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()