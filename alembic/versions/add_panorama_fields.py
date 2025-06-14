"""Add panorama fields to properties table

Revision ID: add_panorama_fields
Revises: 
Create Date: 2024-01-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_panorama_fields'
down_revision = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('properties', schema=None) as batch_op:
        # Добавляем новые поля для 360° панорам
        batch_op.add_column(sa.Column('tour_360_file_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('tour_360_original_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('tour_360_optimized_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('tour_360_preview_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('tour_360_thumbnail_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('tour_360_metadata', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('tour_360_uploaded_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('properties', schema=None) as batch_op:
        # Удаляем добавленные поля
        batch_op.drop_column('tour_360_uploaded_at')
        batch_op.drop_column('tour_360_metadata')
        batch_op.drop_column('tour_360_thumbnail_url')
        batch_op.drop_column('tour_360_preview_url')
        batch_op.drop_column('tour_360_optimized_url')
        batch_op.drop_column('tour_360_original_url')
        batch_op.drop_column('tour_360_file_id')
    # ### end Alembic commands ### 