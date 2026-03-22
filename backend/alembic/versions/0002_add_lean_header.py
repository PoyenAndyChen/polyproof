"""add lean_header to projects

Revision ID: 0002_add_lean_header
Revises: 0001_v4_initial
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_lean_header"
down_revision = "0001_v4_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("lean_header", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "lean_header")
