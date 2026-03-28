"""Add reminder fields to invoices

Revision ID: 002_add_reminder_fields
Revises: 001_add_last_invoiced_date
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_reminder_fields"
down_revision = "001_add_last_invoiced_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("reminder_level", sa.Integer(), server_default="0", nullable=False))
    op.add_column("invoices", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("reminder_pdf_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "reminder_pdf_path")
    op.drop_column("invoices", "reminder_sent_at")
    op.drop_column("invoices", "reminder_level")
