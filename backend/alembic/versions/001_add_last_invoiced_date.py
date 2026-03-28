"""Add last_invoiced_date to contracts

Revision ID: 001_add_last_invoiced_date
Revises:
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = "001_add_last_invoiced_date"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("last_invoiced_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("contracts", "last_invoiced_date")
