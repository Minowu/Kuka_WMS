"""Production & AMR Dispatch Core Models."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import foreign, relationship

from app.core.database import Base


# Mapping status codes sent by KUKA Fleet Manager (ICS/RCS) webhook
MAPPING_STATUS = {
    "6": "in_progress",
    "7": "failed",
    "3": "cancelled",
    "8": "completed",
    "9": "completed",
}


class UserLocation(Base):
    """Assign operators to specific CNC stations or locations (Max 3 per user enforced in service)."""

    __tablename__ = "user_locations"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    location_id = Column(
        Integer,
        ForeignKey("location.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", backref="assigned_locations")
    location = relationship("Location", backref="assigned_users")


class Machine(Base):
    """Master entity for physical CNC machines on the shop floor (3NF)."""

    __tablename__ = "machine"

    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(50), unique=True, nullable=False, index=True)
    machine_name = Column(String(100), nullable=True)
    default_stage_level = Column(Integer, nullable=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    locations = relationship("Location", back_populates="machine")
    route_step_links = relationship(
        "RouteStepMachine",
        back_populates="machine",
        cascade="all, delete-orphan",
    )


class ProductionRoute(Base):
    """Manufacturing route header for a specific product model (Item)."""

    __tablename__ = "production_route"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, nullable=False, index=True)
    route_name = Column(String(100), nullable=False)
    item_id = Column(
        Integer,
        ForeignKey("item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    item = relationship("Item", backref="production_routes")
    steps = relationship(
        "RouteStep",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStep.step_number",
    )


class RouteStep(Base):
    """Detailed CNC processing step within a production route (normalized 3NF)."""

    __tablename__ = "route_step"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(
        Integer,
        ForeignKey("production_route.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number = Column(Integer, nullable=False)
    stage_level = Column(Integer, nullable=False)  # 1: Level 1, 2: Level 2, 3: Level 3...
    step_name = Column(String(100), nullable=False)
    is_final_cnc_step = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("ProductionRoute", back_populates="steps")
    allowed_machine_links = relationship(
        "RouteStepMachine",
        back_populates="route_step",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def allowed_machines(self) -> list[str]:
        """Return list of machine_codes from normalized RouteStepMachine links."""
        return [
            link.machine.machine_code
            for link in (self.allowed_machine_links or [])
            if link.machine and link.machine.machine_code
        ]

    __table_args__ = (
        UniqueConstraint("route_id", "step_number", name="uq_route_step_number"),
        Index("idx_route_step_lookup", "route_id", "stage_level"),
    )


class RouteStepMachine(Base):
    """Many-to-many join table linking RouteStep to allowed physical CNC Machines (3NF)."""

    __tablename__ = "route_step_machine"

    id = Column(Integer, primary_key=True, index=True)
    route_step_id = Column(
        Integer,
        ForeignKey("route_step.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    machine_id = Column(
        Integer,
        ForeignKey("machine.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route_step = relationship("RouteStep", back_populates="allowed_machine_links")
    machine = relationship("Machine", back_populates="route_step_links", lazy="joined")

    __table_args__ = (
        UniqueConstraint("route_step_id", "machine_id", name="uq_route_step_machine"),
    )


class TransportRequest(Base):
    """High-level transport request created by operators or automatic routing."""

    __tablename__ = "transport_request"

    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(50), unique=True, nullable=False, index=True)
    # CALL_MATERIAL | MOVE_NEXT_STAGE | MOVE_TO_WASH | RETURN_EMPTY_CART
    request_type = Column(String(50), nullable=False, default="CALL_MATERIAL")
    item_id = Column(Integer, ForeignKey("item.id"), nullable=True, index=True)
    source_location_id = Column(Integer, ForeignKey("location.id"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
    required_stage_level = Column(Integer, default=0, nullable=False)
    # pending | queued_for_cart | queued_for_slot | in_progress | completed | cancelled | failed
    status = Column(String(30), default="pending", nullable=False, index=True)
    priority = Column(Integer, default=10, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    item = relationship("Item", foreign_keys=[item_id])
    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    cart = relationship("ItemStock", foreign_keys=[cart_id])
    creator = relationship("User", foreign_keys=[created_by])


class TransportQueue(Base):
    """Persistent FIFO queue for requests waiting for an available Cart or CNC Slot."""

    __tablename__ = "transport_queue"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer,
        ForeignKey("transport_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # WAITING_CART | WAITING_SLOT
    queue_type = Column(String(30), nullable=False)
    target_stage_level = Column(Integer, nullable=True)
    # PENDING | PROCESSING | RESOLVED | CANCELLED
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    priority = Column(Integer, default=10, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("TransportRequest", backref="queue_entries")

    __table_args__ = (
        Index("idx_transport_queue_active", "queue_type", "status", "priority"),
    )


class FleetTask(Base):
    """Low-level AMR mission dispatched to KUKA Fleet Manager (RCS/ICS)."""

    __tablename__ = "fleet_task"

    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(50), unique=True, nullable=False, index=True)
    request_id = Column(
        Integer,
        ForeignKey("transport_request.id"),
        nullable=False,
        index=True,
    )
    amr_code = Column(String(50), nullable=True)
    pickup_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    dropoff_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
    process_code = Column(String(50), nullable=True)
    system_code = Column(String(50), nullable=True, default="MES")
    task_order_detail = Column(Text, nullable=True)
    # created | sent | in_progress | completed | failed | cancelled
    status = Column(String(30), default="created", nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    request = relationship("TransportRequest", backref="fleet_tasks")
    pickup_location = relationship("Location", foreign_keys=[pickup_location_id])
    dropoff_location = relationship("Location", foreign_keys=[dropoff_location_id])
    cart = relationship("ItemStock", foreign_keys=[cart_id])
    task_statuses = relationship(
        "TaskStatus",
        primaryjoin="FleetTask.task_code == foreign(TaskStatus.order_id)",
        viewonly=True,
        order_by="TaskStatus.id.desc()",
    )


class TaskStatus(Base):
    """Audit log of raw status callbacks received from KUKA Fleet Manager (/receive-status)."""

    __tablename__ = "task_status"

    id = Column(Integer, primary_key=True, index=True)
    sub_task_status = Column(String(50), nullable=True)
    order_id = Column(String(50), nullable=True, index=True)
    device_code = Column(String(50), nullable=True)
    device_num = Column(String(50), nullable=True)
    qr_code = Column(String(255), nullable=True)
    shelf_number = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fleet_task = relationship(
        "FleetTask",
        primaryjoin="TaskStatus.order_id == foreign(FleetTask.task_code)",
        viewonly=True,
    )


class ProductionRecord(Base):
    """Audit trail of completed CNC machining stages per cart."""

    __tablename__ = "production_record"

    id = Column(Integer, primary_key=True, index=True)
    cart_code = Column(String(50), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False)
    machine_code = Column(String(50), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    stage_level = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    cart = relationship("ItemStock", foreign_keys=[cart_id])
    item = relationship("Item", foreign_keys=[item_id])
    location = relationship("Location", foreign_keys=[location_id])
    operator = relationship("User", foreign_keys=[operator_id])
