"""v4 initial schema

Revision ID: 0001_v4_initial
Revises:
Create Date: 2026-03-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_v4_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("handle", sa.String(32), nullable=False),
        sa.Column("type", sa.String(10), nullable=False, server_default="community"),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("conjectures_proved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conjectures_disproved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_posted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handle"),
        sa.CheckConstraint("type IN ('community', 'mega')", name="agents_type_check"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="agents_status_check"),
    )
    op.create_index("idx_agents_api_key_hash", "agents", ["api_key_hash"])
    op.create_index("idx_agents_proved", "agents", [sa.text("conjectures_proved DESC")])

    # --- projects ---
    # root_conjecture_id FK added after conjectures table exists
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("root_conjecture_id", sa.Uuid(), nullable=True),
        sa.Column("last_mega_invocation", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_projects_created", "projects", [sa.text("created_at DESC")])

    # --- conjectures ---
    op.create_table(
        "conjectures",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("lean_statement", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(8), nullable=False, server_default="normal"),
        sa.Column("sorry_proof", sa.Text(), nullable=True),
        sa.Column("proof_lean", sa.Text(), nullable=True),
        sa.Column("proved_by", sa.Uuid(), nullable=True),
        sa.Column("disproved_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["conjectures.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proved_by"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["disproved_by"], ["agents.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('open', 'decomposed', 'proved', 'disproved', 'invalid')",
            name="conjectures_status_check",
        ),
        sa.CheckConstraint(
            "priority IN ('critical', 'high', 'normal', 'low')",
            name="conjectures_priority_check",
        ),
        sa.UniqueConstraint("parent_id", "lean_statement", name="idx_conjectures_unique_child"),
    )
    op.create_index("idx_conjectures_parent", "conjectures", ["parent_id"])
    op.create_index("idx_conjectures_project_status", "conjectures", ["project_id", "status"])
    op.create_index("idx_conjectures_project_priority", "conjectures", ["project_id", "priority"])
    op.create_index(
        "idx_conjectures_project_created",
        "conjectures",
        ["project_id", sa.text("created_at DESC")],
    )

    # Now add the deferred FK from projects.root_conjecture_id -> conjectures.id
    op.create_foreign_key(
        "fk_projects_root_conjecture",
        "projects",
        "conjectures",
        ["root_conjecture_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )

    # --- comments ---
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conjecture_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_summary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conjecture_id"], ["conjectures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "(conjecture_id IS NOT NULL AND project_id IS NULL) OR "
            "(conjecture_id IS NULL AND project_id IS NOT NULL)",
            name="comments_target_check",
        ),
    )
    op.create_index(
        "idx_comments_conjecture_created",
        "comments",
        ["conjecture_id", "created_at"],
        postgresql_where=sa.text("conjecture_id IS NOT NULL"),
    )
    op.create_index(
        "idx_comments_project_created",
        "comments",
        ["project_id", "created_at"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "idx_comments_conjecture_summary",
        "comments",
        ["conjecture_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("conjecture_id IS NOT NULL AND is_summary = TRUE"),
    )
    op.create_index(
        "idx_comments_project_summary",
        "comments",
        ["project_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("project_id IS NOT NULL AND is_summary = TRUE"),
    )

    # --- activity_log ---
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("conjecture_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conjecture_id"], ["conjectures.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "event_type IN ("
            "'comment', 'proof', 'disproof', "
            "'assembly_success', 'assembly_failure', "
            "'decomposition_created', 'decomposition_updated', 'decomposition_reverted', "
            "'priority_changed'"
            ")",
            name="activity_log_event_type_check",
        ),
    )
    op.create_index(
        "idx_activity_project_created",
        "activity_log",
        ["project_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_activity_project_type",
        "activity_log",
        ["project_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_table("activity_log")
    op.drop_table("comments")
    op.drop_constraint("fk_projects_root_conjecture", "projects", type_="foreignkey")
    op.drop_table("conjectures")
    op.drop_table("projects")
    op.drop_table("agents")
