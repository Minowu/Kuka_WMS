"""align kuka fleet nomenclature

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-10-21 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    # 1. fleet_task table renames & additions
    op.alter_column('fleet_task', 'task_code', new_column_name='mission_code')
    op.execute('ALTER INDEX IF EXISTS ix_fleet_task_task_code RENAME TO ix_fleet_task_mission_code')
    
    op.alter_column('fleet_task', 'request_id', new_column_name='transport_request_id')
    op.alter_column('fleet_task', 'amr_code', new_column_name='robot_id')
    op.alter_column('fleet_task', 'cart_id', new_column_name='container_id')
    
    op.add_column('fleet_task', sa.Column('fleet_request_id', sa.String(length=50), nullable=True))
    op.add_column('fleet_task', sa.Column('container_code', sa.String(length=50), nullable=True))
    
    op.alter_column('fleet_task', 'task_order_detail', new_column_name='mission_data')
    
    op.add_column('fleet_task', sa.Column('last_mission_status', sa.String(length=30), nullable=True))
    op.add_column('fleet_task', sa.Column('current_position', sa.String(length=50), nullable=True))
    op.add_column('fleet_task', sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('fleet_task', sa.Column('submit_attempts', sa.Integer(), server_default='0', nullable=False))
    
    op.drop_column('fleet_task', 'process_code')
    op.drop_column('fleet_task', 'system_code')

    # 2. task_status table renames & additions
    op.drop_column('task_status', 'sub_task_status')
    op.drop_column('task_status', 'device_num')
    op.drop_column('task_status', 'qr_code')
    
    op.alter_column('task_status', 'order_id', new_column_name='mission_code')
    op.execute('ALTER INDEX IF EXISTS ix_task_status_order_id RENAME TO ix_task_status_mission_code')
    
    op.alter_column('task_status', 'device_code', new_column_name='robot_id')
    op.alter_column('task_status', 'shelf_number', new_column_name='container_code')
    op.alter_column('task_status', 'status', new_column_name='mission_status')
    
    op.add_column('task_status', sa.Column('org_id', sa.String(length=50), nullable=True))
    op.add_column('task_status', sa.Column('container_location_code', sa.String(length=50), nullable=True))
    op.add_column('task_status', sa.Column('current_position', sa.String(length=50), nullable=True))
    op.add_column('task_status', sa.Column('robot_x', sa.Numeric(precision=10, scale=3), nullable=True))
    op.add_column('task_status', sa.Column('robot_y', sa.Numeric(precision=10, scale=3), nullable=True))
    op.add_column('task_status', sa.Column('map_code', sa.String(length=50), nullable=True))
    op.add_column('task_status', sa.Column('message', sa.String(length=255), nullable=True))
    op.add_column('task_status', sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 3. item_stock table renames & additions
    op.alter_column('item_stock', 'cart_code', new_column_name='container_code')
    op.execute('ALTER INDEX IF EXISTS ix_item_stock_cart_code RENAME TO ix_item_stock_container_code')
    op.alter_column('item_stock', 'locked_by_task_id', new_column_name='locked_by_mission_code')
    op.add_column('item_stock', sa.Column('fleet_registered', sa.Boolean(), server_default='false', nullable=False))

    # 4. transport_request table renames
    op.alter_column('transport_request', 'cart_id', new_column_name='container_id')

    # 5. production_record table renames
    op.alter_column('production_record', 'cart_code', new_column_name='container_code')
    op.execute('ALTER INDEX IF EXISTS ix_production_record_cart_code RENAME TO ix_production_record_container_code')
    op.alter_column('production_record', 'cart_id', new_column_name='container_id')

    # 6. fleet_api_call new table
    op.create_table(
        'fleet_api_call',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('api_name', sa.String(length=50), nullable=False),
        sa.Column('request_id', sa.String(length=50), unique=True, nullable=False),
        sa.Column('mission_code', sa.String(length=50), nullable=True, index=True),
        sa.Column('container_code', sa.String(length=50), nullable=True),
        sa.Column('request_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('response_body', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('fleet_api_call')
    
    op.alter_column('production_record', 'container_id', new_column_name='cart_id')
    op.alter_column('production_record', 'container_code', new_column_name='cart_code')
    op.execute('ALTER INDEX IF EXISTS ix_production_record_container_code RENAME TO ix_production_record_cart_code')

    op.alter_column('transport_request', 'container_id', new_column_name='cart_id')

    op.drop_column('item_stock', 'fleet_registered')
    op.alter_column('item_stock', 'locked_by_mission_code', new_column_name='locked_by_task_id')
    op.alter_column('item_stock', 'container_code', new_column_name='cart_code')
    op.execute('ALTER INDEX IF EXISTS ix_item_stock_container_code RENAME TO ix_item_stock_cart_code')

    op.drop_column('task_status', 'raw_payload')
    op.drop_column('task_status', 'message')
    op.drop_column('task_status', 'map_code')
    op.drop_column('task_status', 'robot_y')
    op.drop_column('task_status', 'robot_x')
    op.drop_column('task_status', 'current_position')
    op.drop_column('task_status', 'container_location_code')
    op.drop_column('task_status', 'org_id')
    op.alter_column('task_status', 'mission_status', new_column_name='status')
    op.alter_column('task_status', 'container_code', new_column_name='shelf_number')
    op.alter_column('task_status', 'robot_id', new_column_name='device_code')
    op.alter_column('task_status', 'mission_code', new_column_name='order_id')
    op.execute('ALTER INDEX IF EXISTS ix_task_status_mission_code RENAME TO ix_task_status_order_id')
    op.add_column('task_status', sa.Column('qr_code', sa.String(length=255), nullable=True))
    op.add_column('task_status', sa.Column('device_num', sa.String(length=50), nullable=True))
    op.add_column('task_status', sa.Column('sub_task_status', sa.String(length=50), nullable=True))

    op.add_column('fleet_task', sa.Column('system_code', sa.String(length=50), nullable=True))
    op.add_column('fleet_task', sa.Column('process_code', sa.String(length=50), nullable=True))
    op.drop_column('fleet_task', 'submit_attempts')
    op.drop_column('fleet_task', 'picked_up_at')
    op.drop_column('fleet_task', 'current_position')
    op.drop_column('fleet_task', 'last_mission_status')
    op.alter_column('fleet_task', 'mission_data', new_column_name='task_order_detail')
    op.drop_column('fleet_task', 'container_code')
    op.drop_column('fleet_task', 'fleet_request_id')
    op.alter_column('fleet_task', 'container_id', new_column_name='cart_id')
    op.alter_column('fleet_task', 'robot_id', new_column_name='amr_code')
    op.alter_column('fleet_task', 'transport_request_id', new_column_name='request_id')
    op.alter_column('fleet_task', 'mission_code', new_column_name='task_code')
    op.execute('ALTER INDEX IF EXISTS ix_fleet_task_mission_code RENAME TO ix_fleet_task_task_code')
