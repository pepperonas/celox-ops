"""Add credit notes and partial payments fields to invoices

Revision ID: 004_credit_notes_payments
Revises: 003_add_quote_fields
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004_credit_notes_payments"
down_revision = "003_add_quote_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("amount_paid", sa.Numeric(12, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "invoices",
        sa.Column("credit_note_for", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("is_credit_note", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_foreign_key(
        "fk_invoices_credit_note_for",
        "invoices",
        "invoices",
        ["credit_note_for"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_invoices_credit_note_for", "invoices", type_="foreignkey")
    op.drop_column("invoices", "is_credit_note")
    op.drop_column("invoices", "credit_note_for")
    op.drop_column("invoices", "amount_paid")
