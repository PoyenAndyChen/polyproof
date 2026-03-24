"""Service for serving tracked file content from the workspace."""

import os
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.tracked_file import TrackedFile


async def get_content(db: AsyncSession, file_id: UUID) -> str | None:
    """Read file content from the project workspace.

    Returns the file content as a string, or None if the file or project is not found.
    """
    result = await db.execute(
        select(TrackedFile, Project)
        .join(Project, TrackedFile.project_id == Project.id)
        .where(TrackedFile.id == file_id)
    )
    row = result.first()
    if row is None:
        return None

    tracked_file, project = row
    full_path = os.path.join(project.workspace_path, tracked_file.file_path)

    if not os.path.isfile(full_path):
        return None

    with open(full_path) as f:
        return f.read()
