"""
Production and AMR dispatch SQLAlchemy models for KUKA machining workshop.

3NF normalized structure:
- `Machine`: physical CNC machines.
- `Location`: slots / parking points (CNC_SLOT, RAW_MATERIAL, WASHING_SLOT, EMPTY_CART_BUFFER).
- `ProductionRoute`, `RouteStep`, `RouteStepMachine`: route definition per Model.
- `TransportRequest`: high-level transport intent from operator or automated logic.
- `TransportQueue`: FIFO queues (WAITING_CART, WAITING_SLOT).
- `FleetTask`: low-level AMR mission dispatched to KUKA Fleet Manager (/amr/submitMission).
- `TaskStatus`: audit log of callbacks received from KUKA Fleet Manager (/receive-status).
- `FleetApiCall`: audit log of outbound API calls to KUKA Fleet Manager.
- `ProductionRecord`: completion audit trail per container.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import foreign, relationship, synonym

from app.core.database import Base


# Real KUKA Fleet Mission Statuses
FLEET_MISSION_STATUS = {
    "MOVE_BEGIN": "in_progress",
    "ARRIVED": "in_progress",
    "UP_CONTAINER": "in_progress",
    "DOWN_CONTAINER": "in_progress",  # D2: Still in_progress!
    "COMPLETED": "completed",         # D2: Only completion signal!
    "FAILED": "failed",
    "CANCELLED": "cancelled",
    "CANCEL": "cancelled",
}

# Compatibility alias
MAPPING_STATUS = FLEET_MISSION_STATUS


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
    machine_name = Column(String(100), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    locations = relationship(
        "Location",
        primaryjoin="Location.machine_id == Machine.id",
        order_by="Location.position_index",
        back_populates="machine",
    )
    slots = synonym("locations")


class ProductionRoute(Base):
    """Production route definition per Item (Model)."""

    __tablename__ = "production_route"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, nullable=False, index=True)
    route_name = Column(String(100), nullable=False)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
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
        backref="route",
        cascade="all, delete-orphan",
        order_by="RouteStep.step_number",
    )


class RouteStep(Base):
    """A processing stage within a production route (3NF: normalized step)."""

    __tablename__ = "route_step"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(
        Integer,
        ForeignKey("production_route.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number = Column(Integer, nullable=False)
    stage_level = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    is_final_cnc_step = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("route_id", "step_number", name="uq_route_step_number"),
        UniqueConstraint("route_id", "stage_level", name="uq_route_stage_level"),
    )

    allowed_machine_links = relationship(
        "RouteStepMachine",
        backref="route_step",
        cascade="all, delete-orphan",
    )
    step_machines = synonym("allowed_machine_links")

    @property
    def allowed_machines(self) -> list[str]:
        if not self.allowed_machine_links:
            return []
        return [
            link.machine.machine_code
            for link in self.allowed_machine_links
            if link.machine and link.machine.machine_code
        ]


class RouteStepMachine(Base):
    """Association table linking RouteStep to Machine (3NF bridge table)."""

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

    machine = relationship("Machine")

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
    container_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
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
    container = relationship("ItemStock", foreign_keys=[container_id])
    creator = relationship("User", foreign_keys=[created_by])

    @property
    def cart(self):
        return self.container

    @cart.setter
    def cart(self, value):
        self.container = value


class TransportQueue(Base):
    """Persistent FIFO queue for requests waiting for an available Container or CNC Slot."""

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
    """Low-level AMR mission dispatched to KUKA Fleet Manager (/amr/submitMission)."""

    __tablename__ = "fleet_task"

    id = Column(Integer, primary_key=True, index=True)
    mission_code = Column(String(50), unique=True, nullable=False, index=True)
    transport_request_id = Column(
        Integer,
        ForeignKey("transport_request.id"),
        nullable=False,
        index=True,
    )
    fleet_request_id = Column(String(50), nullable=True)
    robot_id = Column(String(50), nullable=True)
    pickup_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    dropoff_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
    container_code = Column(String(50), nullable=True)
    mission_data = Column(JSONB, nullable=True)
    last_mission_status = Column(String(30), nullable=True)
    current_position = Column(String(50), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    submit_attempts = Column(Integer, default=0, nullable=False)

    # created | pending_submit | sent | in_progress | completed | failed | cancelled
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

    request = relationship("TransportRequest", backref="fleet_tasks", foreign_keys=[transport_request_id])
    pickup_location = relationship("Location", foreign_keys=[pickup_location_id])
    dropoff_location = relationship("Location", foreign_keys=[dropoff_location_id])
    container = relationship("ItemStock", foreign_keys=[container_id])
    task_statuses = relationship(
        "TaskStatus",
        primaryjoin="FleetTask.mission_code == foreign(TaskStatus.mission_code)",
        viewonly=True,
        order_by="TaskStatus.id.desc()",
    )


class TaskStatus(Base):
    """Audit log of status callbacks received from KUKA Fleet Manager (/receive-status)."""

    __tablename__ = "task_status"

    id = Column(Integer, primary_key=True, index=True)
    mission_code = Column(String(50), nullable=True, index=True)
    robot_id = Column(String(50), nullable=True)
    container_code = Column(String(50), nullable=True)
    mission_status = Column(String(50), nullable=True)
    org_id = Column(String(50), nullable=True)
    container_location_code = Column(String(50), nullable=True)
    current_position = Column(String(50), nullable=True)
    robot_x = Column(Numeric(10, 3), nullable=True)
    robot_y = Column(Numeric(10, 3), nullable=True)
    map_code = Column(String(50), nullable=True)
    message = Column(String(255), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fleet_task = relationship(
        "FleetTask",
        primaryjoin="TaskStatus.mission_code == foreign(FleetTask.mission_code)",
        viewonly=True,
    )


class FleetApiCall(Base):
    """Audit log of outbound API calls dispatched to KUKA Fleet Manager."""

    __tablename__ = "fleet_api_call"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_name = Column(String(50), nullable=False)
    request_id = Column(String(50), unique=True, nullable=False, index=True)
    mission_code = Column(String(50), nullable=True, index=True)
    container_code = Column(String(50), nullable=True)
    request_body = Column(JSONB, nullable=False)
    http_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProductionRecord(Base):
    """Audit trail of completed CNC machining stages per container."""

    __tablename__ = "production_record"

    id = Column(Integer, primary_key=True, index=True)
    container_code = Column(String(50), nullable=False, index=True)
    container_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False)
    machine_code = Column(String(50), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    stage_level = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    container = relationship("ItemStock", foreign_keys=[container_id])
    item = relationship("Item", foreign_keys=[item_id])
    location = relationship("Location", foreign_keys=[location_id])
    operator = relationship("User", foreign_keys=[operator_id])
