from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.connection import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'compiling', 'merged', 'failed', 'superseded')",
            name="jobs_status_check",
        ),
        CheckConstraint(
            "job_type IN ('fill', 'upstream_pull')",
            name="jobs_type_check",
        ),
        Index("idx_jobs_project_status", "project_id", "status"),
        Index("idx_jobs_sorry_status", "sorry_id", "status"),
        Index("idx_jobs_created", text("created_at DESC")),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    sorry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sorries.id", ondelete="SET NULL"),
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
    )
    job_type: Mapped[str] = mapped_column(String(20), default="fill", nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="queued", nullable=False)
    tactics: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    lean_output: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
