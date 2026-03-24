from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.connection import Base


class Sorry(Base):
    __tablename__ = "sorries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'decomposed', 'filled', 'filled_externally', 'invalid')",
            name="sorries_status_check",
        ),
        CheckConstraint(
            "priority IN ('critical', 'high', 'normal', 'low')",
            name="sorries_priority_check",
        ),
        Index("idx_sorries_file", "file_id"),
        Index("idx_sorries_project_status", "project_id", "status"),
        Index("idx_sorries_project_priority", "project_id", "priority"),
        Index("idx_sorries_project_created", "project_id", text("created_at DESC")),
        Index("idx_sorries_parent", "parent_sorry_id"),
        Index(
            "idx_sorries_identity",
            "file_id",
            "declaration_name",
            "sorry_index",
            "goal_hash",
            unique=True,
            postgresql_where=text("status NOT IN ('invalid', 'filled', 'filled_externally')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracked_files.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    declaration_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sorry_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goal_state: Mapped[str] = mapped_column(Text, nullable=False)
    local_context: Mapped[str | None] = mapped_column(Text)
    goal_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String(8), default="normal", nullable=False)
    active_agents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filled_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
    )
    fill_tactics: Mapped[str | None] = mapped_column(Text)
    fill_description: Mapped[str | None] = mapped_column(Text)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_sorry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sorries.id", ondelete="SET NULL"),
    )
    line: Mapped[int | None] = mapped_column(Integer)
    col: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
