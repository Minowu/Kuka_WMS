"""add audit_logs, action_logs, devices + audit permissions

Revision ID: d9e0f1a2b3c4
Revises: b1c2d3e4f5a6
Create Date: 2026-11-10 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd9e0f1a2b3c4'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    ("audit:read", "Xem audit/action log", "audit", "Xem nhật ký đăng nhập và thao tác"),
    ("device:manage", "Quản lý thiết bị", "audit", "Thêm/sửa/xoá ánh xạ IP -> tên thiết bị"),
    ("user:create", "Tạo tài khoản", "auth", "Tạo tài khoản người dùng mới"),
]


def upgrade():
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('device_type', sa.String(length=20), nullable=False, server_default='pda'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_devices_id', 'devices', ['id'])
    op.create_index('ix_devices_ip_address', 'devices', ['ip_address'], unique=True)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('result', sa.String(length=10), nullable=False),
        sa.Column('failure_reason', sa.String(length=50), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('device_type', sa.String(length=20), nullable=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_event_created', 'audit_logs', ['event_type', 'created_at'])

    op.create_table(
        'action_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('route_template', sa.String(length=255), nullable=True),
        sa.Column('path', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=50), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(length=10), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('query_params', postgresql.JSONB(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('device_type', sa.String(length=20), nullable=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_action_logs_created_at', 'action_logs', ['created_at'])
    op.create_index('ix_action_logs_user_created', 'action_logs', ['user_id', 'created_at'])
    op.create_index('ix_action_logs_action_created', 'action_logs', ['action', 'created_at'])

    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('module', sa.String),
        sa.column('description', sa.String),
    )
    for code, name, module, description in NEW_PERMISSIONS:
        op.execute(
            postgresql.insert(permissions)
            .values(code=code, name=name, module=module, description=description)
            .on_conflict_do_nothing(index_elements=['code'])
        )


def downgrade():
    op.execute(
        "DELETE FROM permissions WHERE code IN ('audit:read', 'device:manage')"
    )
    op.drop_table('action_logs')
    op.drop_table('audit_logs')
    op.drop_index('ix_devices_ip_address', table_name='devices')
    op.drop_index('ix_devices_id', table_name='devices')
    op.drop_table('devices')
