from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.connection import Base


class TrackedFile(Base):
    __tablename__ = "tracked_files"
    __table_args__ = (
        Index("idx_tracked_files_project", "project_id"),
        Index("idx_tracked_files_path", "project_id", "file_path", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sorry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_compiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
