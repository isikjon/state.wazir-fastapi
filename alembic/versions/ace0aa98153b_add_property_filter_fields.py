"""add_property_filter_fields

Revision ID: ace0aa98153b
Revises: 52fa2e84fc29
Create Date: 2025-05-21 21:38:07.746421

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ace0aa98153b'
down_revision = '52fa2e84fc29'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем все необходимые поля в таблицу properties
    op.add_column('properties', sa.Column('rooms', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('floor', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('building_floors', sa.Integer(), nullable=True))
    op.add_column('properties', sa.Column('has_balcony', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('properties', sa.Column('has_furniture', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('properties', sa.Column('has_renovation', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('properties', sa.Column('has_parking', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    # Удаляем добавленные колонки в случае отката миграции
    op.drop_column('properties', 'has_parking')
    op.drop_column('properties', 'has_renovation')
    op.drop_column('properties', 'has_furniture')
    op.drop_column('properties', 'has_balcony')
    op.drop_column('properties', 'building_floors')
    op.drop_column('properties', 'floor')
    op.drop_column('properties', 'rooms') 