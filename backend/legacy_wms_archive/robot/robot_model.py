"""Robot task model for inbound/outbound order automation."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, case, select, table, column

from sqlalchemy.orm import foreign, relationship, column_property

from app.core.database import Base


MAPPING_STATUS = {
    "6": "in_progress",
    "7": "failed",
    "3": "cancelled",
    "8": "completed",
    "9": "completed"
}

def _mapped_task_status_expr(raw_status_col):
    """Map mã ICS → status WMS; không khớp hoặc NULL → initialize."""
    return case(
        *[
            (raw_status_col == code, mapped)
            for code, mapped in MAPPING_STATUS.items()
        ],
        else_="initialize",
    )

_task_status_tbl = table(
    "task_status",
    column("id", Integer),
    column("order_id", String),
    column("status", String),
    column("created_at", DateTime(timezone=True)),
)

class RobotTask(Base):
    """Store robot task data for inbound and outbound orders."""

    __tablename__ = "robot_task"

    id = Column(Integer, primary_key=True, index=True)
    inbound_order_detail_id = Column(
        Integer,
        ForeignKey("inbound_order_detail.id"),
        nullable=True,
        index=True,
    )

    # Parent order id (inbound_order.id or outbound_order.id); no single FK table.
    order_id = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    process_code = Column(String(50), nullable=False)
    system_code = Column(String(50), nullable=False)
    task_order_detail = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inbound_order_detail = relationship(
        "InboundOrderDetail",
        foreign_keys=[inbound_order_detail_id],
        lazy="joined",
    )
    outbound_order_allocations = relationship(
        "OutboundOrderAllocation",
        primaryjoin="RobotTask.id == foreign(OutboundOrderAllocation.robot_task_id)",
        viewonly=True,
    )

    task_statuses = relationship(
        "TaskStatus",
        primaryjoin="RobotTask.order_id == foreign(TaskStatus.order_id)",
        viewonly=True,
    )

    status = column_property(
        func.coalesce(
            select(
                _mapped_task_status_expr(_task_status_tbl.c.status)
            )
            .where(_task_status_tbl.c.order_id == order_id)
            .order_by(
                _task_status_tbl.c.created_at.desc(),
                _task_status_tbl.c.id.desc(),
            )
            .limit(1)
            .correlate_except(_task_status_tbl)
            .scalar_subquery(),
            "initialize",  
        )
    )

class TaskStatus(Base):

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

    robot_tasks = relationship(
        "RobotTask",
        primaryjoin="TaskStatus.order_id == foreign(RobotTask.order_id)",
        viewonly=True,
    )