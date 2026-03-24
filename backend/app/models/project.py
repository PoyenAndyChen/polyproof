from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.connection import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("idx_projects_created", text("created_at DESC")),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    upstream_repo: Mapped[str] = mapped_column(String(500), nullable=False)
    upstream_branch: Mapped[str] = mapped_column(String(100), default="master", nullable=False)
    fork_repo: Mapped[str] = mapped_column(String(500), nullable=False)
    fork_branch: Mapped[str] = mapped_column(String(100), default="polyproof", nullable=False)
    current_commit: Mapped[str | None] = mapped_column(String(40))
    upstream_commit: Mapped[str | None] = mapped_column(String(40))
    lean_toolchain: Mapped[str] = mapped_column(String(100), nullable=False)
    workspace_path: Mapped[str] = mapped_column(String(500), nullable=False)
    last_mega_invocation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
