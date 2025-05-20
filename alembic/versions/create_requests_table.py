"""create requests table

Revision ID: 52fa2e84fc29
Revises: d0bf329ab48c
Create Date: 2024-05-20 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52fa2e84fc29'
down_revision = 'd0bf329ab48c'
branch_labels = None
depends_on = None


def upgrade():
    # Создание таблицы requests с ENUM прямо в определении колонок (MySQL синтаксис)
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.Enum('viewing', 'purchase', 'sell', 'consultation', 'other', name='requesttype'), nullable=True),
        sa.Column('status', sa.Enum('new', 'processing', 'completed', 'rejected', name='requeststatus'), nullable=True),
        sa.Column('appointment_date', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_urgent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requests_id'), 'requests', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_requests_id'), table_name='requests')
    op.drop_table('requests') 