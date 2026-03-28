"""Add quote fields to orders

Revision ID: 003_add_quote_fields
Revises: 002_add_reminder_fields
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_quote_fields"
down_revision = "002_add_reminder_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("positions", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("quote_pdf_path", sa.String(500), nullable=True))
    op.add_column("orders", sa.Column("valid_until", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "valid_until")
    op.drop_column("orders", "quote_pdf_path")
    op.drop_column("orders", "positions")
