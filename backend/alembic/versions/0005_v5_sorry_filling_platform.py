"""v5: sorry-filling platform

Complete v5 schema. Creates all tables from scratch:
owners, agents, email_verification_tokens, projects, tracked_files, sorries,
jobs, comments, activity_log.

Revision ID: 0005
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- owners ---
    op.create_table(
        "owners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("twitter_id", sa.String(64), nullable=True),
        sa.Column("twitter_handle", sa.String(64), nullable=True),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("handle", sa.String(32), nullable=False),
        sa.Column("type", sa.String(10), nullable=False, server_default="community"),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("sorries_filled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sorries_decomposed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_posted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("claim_token_hash", sa.String(64), nullable=True),
        sa.Column("verification_code", sa.String(20), nullable=True),
        sa.Column("is_claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("last_dashboard_visit", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type IN ('community', 'mega')", name="agents_type_check"),
        sa.CheckConstraint("status IN ('active', 'suspended', 'pending_claim')", name="agents_status_check"),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handle"),
    )
    op.create_index("idx_agents_api_key_hash", "agents", ["api_key_hash"])
    op.create_index("idx_agents_filled", "agents", [sa.text("sorries_filled DESC")])
    op.create_index("idx_agents_claim_token", "agents", ["claim_token_hash"])

    # --- email_verification_tokens ---
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("claim_token_hash", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_email_verification_token_hash", "email_verification_tokens", ["token_hash"])

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("upstream_repo", sa.String(500), nullable=False),
        sa.Column("upstream_branch", sa.String(100), nullable=False, server_default="master"),
        sa.Column("fork_repo", sa.String(500), nullable=False),
        sa.Column("fork_branch", sa.String(100), nullable=False, server_default="polyproof"),
        sa.Column("current_commit", sa.String(40), nullable=True),
        sa.Column("upstream_commit", sa.String(40), nullable=True),
        sa.Column("lean_toolchain", sa.String(100), nullable=False),
        sa.Column("workspace_path", sa.String(500), nullable=False),
        sa.Column("last_mega_invocation", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_projects_created", "projects", [sa.text("created_at DESC")])

    # --- tracked_files ---
    op.create_table(
        "tracked_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("sorry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_compiled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tracked_files_project", "tracked_files", ["project_id"])
    op.create_index("idx_tracked_files_path", "tracked_files", ["project_id", "file_path"], unique=True)

    # --- sorries ---
    op.create_table(
        "sorries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("declaration_name", sa.String(500), nullable=False),
        sa.Column("sorry_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goal_state", sa.Text(), nullable=False),
        sa.Column("local_context", sa.Text(), nullable=True),
        sa.Column("goal_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(8), nullable=False, server_default="normal"),
        sa.Column("active_agents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filled_by", sa.Uuid(), nullable=True),
        sa.Column("fill_tactics", sa.Text(), nullable=True),
        sa.Column("fill_description", sa.Text(), nullable=True),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_sorry_id", sa.Uuid(), nullable=True),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("col", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'decomposed', 'filled', 'filled_externally', 'invalid')",
            name="sorries_status_check",
        ),
        sa.CheckConstraint("priority IN ('critical', 'high', 'normal', 'low')", name="sorries_priority_check"),
        sa.ForeignKeyConstraint(["file_id"], ["tracked_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["filled_by"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_sorry_id"], ["sorries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sorries_file", "sorries", ["file_id"])
    op.create_index("idx_sorries_project_status", "sorries", ["project_id", "status"])
    op.create_index("idx_sorries_project_priority", "sorries", ["project_id", "priority"])
    op.create_index("idx_sorries_project_created", "sorries", ["project_id", sa.text("created_at DESC")])
    op.create_index("idx_sorries_parent", "sorries", ["parent_sorry_id"])
    op.create_index(
        "idx_sorries_identity",
        "sorries",
        ["file_id", "declaration_name", "sorry_index", "goal_hash"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('invalid', 'filled', 'filled_externally')"),
    )

    # --- jobs ---
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("sorry_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("job_type", sa.String(20), nullable=False, server_default="fill"),
        sa.Column("status", sa.String(12), nullable=False, server_default="queued"),
        sa.Column("tactics", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lean_output", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'compiling', 'merged', 'failed', 'superseded')",
            name="jobs_status_check",
        ),
        sa.CheckConstraint("job_type IN ('fill', 'upstream_pull')", name="jobs_type_check"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sorry_id"], ["sorries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_jobs_project_status", "jobs", ["project_id", "status"])
    op.create_index("idx_jobs_sorry_status", "jobs", ["sorry_id", "status"])
    op.create_index("idx_jobs_created", "jobs", [sa.text("created_at DESC")])

    # --- comments ---
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sorry_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_summary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(sorry_id IS NOT NULL AND project_id IS NULL) OR "
            "(sorry_id IS NULL AND project_id IS NOT NULL)",
            name="comments_target_check",
        ),
        sa.ForeignKeyConstraint(["sorry_id"], ["sorries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_comments_sorry_created", "comments", ["sorry_id", "created_at"],
        postgresql_where=sa.text("sorry_id IS NOT NULL"),
    )
    op.create_index(
        "idx_comments_project_created", "comments", ["project_id", "created_at"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "idx_comments_sorry_summary", "comments", ["sorry_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("sorry_id IS NOT NULL AND is_summary = TRUE"),
    )
    op.create_index(
        "idx_comments_project_summary", "comments", ["project_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("project_id IS NOT NULL AND is_summary = TRUE"),
    )

    # --- activity_log ---
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("sorry_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('comment', 'fill', 'decomposition', 'fill_reverted', 'priority_changed')",
            name="activity_log_event_type_check",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sorry_id"], ["sorries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_activity_project_created", "activity_log", ["project_id", sa.text("created_at DESC")])
    op.create_index("idx_activity_project_type", "activity_log", ["project_id", "event_type"])


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for v5 migration")
