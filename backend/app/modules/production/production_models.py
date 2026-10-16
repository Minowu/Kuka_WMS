"""Production and dispatching models for KUKA AMR CNC machining pipeline."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserLocation(Base):
    """Maps operators/users to their authorized physical stations/locations."""

    __tablename__ = "user_locations"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    location_id = Column(
        Integer,
        ForeignKey("location.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    location = relationship("Location", foreign_keys=[location_id], lazy="joined")


class ProductionRoute(Base):
    """Technological routing definition for a part model."""

    __tablename__ = "production_route"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, nullable=False, index=True)
    route_name = Column(String(100), nullable=False)
    item_id = Column(Integer, ForeignKey("item.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    item = relationship("Item", foreign_keys=[item_id], lazy="joined")
    steps = relationship(
        "RouteStep",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStep.step_number",
        lazy="selectin",
    )


class RouteStep(Base):
    """Individual process step within a production route."""

    __tablename__ = "route_step"
    __table_args__ = (
        UniqueConstraint("route_id", "step_number", name="uq_route_step_number"),
        Index("idx_route_step_lookup", "route_id", "stage_level"),
    )

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("production_route.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    stage_level = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    allowed_machines = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
    is_final_cnc_step = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("ProductionRoute", back_populates="steps")


class TransportRequest(Base):
    """Human or automated transport request generated from PDA or workflow."""

    __tablename__ = "transport_request"

    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(50), unique=True, nullable=False, index=True)
    request_type = Column(
        String(50),
        nullable=False,
        default="CALL_MATERIAL",
        server_default="CALL_MATERIAL",
    )  # 'CALL_MATERIAL', 'MOVE_WIP', 'SEND_TO_WASH', 'RETURN_EMPTY_CART'
    item_id = Column(Integer, ForeignKey("item.id"), nullable=True, index=True)
    source_location_id = Column(Integer, ForeignKey("location.id"), nullable=True, index=True)
    destination_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True, index=True)
    required_stage_level = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )  # 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'
    priority = Column(Integer, nullable=False, default=10, server_default="10")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    item = relationship("Item", foreign_keys=[item_id], lazy="joined")
    source_location = relationship("Location", foreign_keys=[source_location_id], lazy="joined")
    destination_location = relationship("Location", foreign_keys=[destination_location_id], lazy="joined")
    cart = relationship("ItemStock", foreign_keys=[cart_id], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    queue_entries = relationship("TransportQueue", back_populates="request", cascade="all, delete-orphan")
    fleet_tasks = relationship("FleetTask", back_populates="request")


class TransportQueue(Base):
    """Backpressure queue when no matching cart or washing slot is currently available."""

    __tablename__ = "transport_queue"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer,
        ForeignKey("transport_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_type = Column(String(30), nullable=False)  # 'WAITING_CART', 'WAITING_WASH_SLOT'
    target_stage_level = Column(Integer, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )  # 'PENDING', 'PROCESSING', 'RESOLVED', 'CANCELLED'
    retry_count = Column(Integer, nullable=False, default=0, server_default="0")
    priority = Column(Integer, nullable=False, default=10, server_default="10")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("TransportRequest", back_populates="queue_entries")


class FleetTask(Base):
    """Robot hardware task dispatched to KUKA AMR Fleet Manager / RCS."""

    __tablename__ = "fleet_task"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50), unique=True, nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("transport_request.id"), nullable=False, index=True)
    amr_code = Column(String(50), nullable=True, index=True)
    pickup_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    dropoff_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True, index=True)
    status = Column(
        String(30),
        nullable=False,
        default="created",
        server_default="created",
        index=True,
    )  # 'created', 'sent', 'executing', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    request = relationship("TransportRequest", back_populates="fleet_tasks")
    pickup_location = relationship("Location", foreign_keys=[pickup_location_id], lazy="joined")
    dropoff_location = relationship("Location", foreign_keys=[dropoff_location_id], lazy="joined")
    cart = relationship("ItemStock", foreign_keys=[cart_id], lazy="joined")


class ProductionRecord(Base):
    """Traceability log recording each stage completion across CNC machines."""

    __tablename__ = "production_record"

    id = Column(Integer, primary_key=True, index=True)
    cart_code = Column(String(50), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False, index=True)
    machine_code = Column(String(50), nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    stage_level = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    item = relationship("Item", foreign_keys=[item_id], lazy="joined")
    location = relationship("Location", foreign_keys=[location_id], lazy="joined")
    cart = relationship("ItemStock", foreign_keys=[cart_id], lazy="joined")
    operator = relationship("User", foreign_keys=[operator_id], lazy="joined")
