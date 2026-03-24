"""Service for serving tracked file content from the project's GitHub fork."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.tracked_file import TrackedFile
from app.services import github_service

logger = logging.getLogger(__name__)


async def get_content(db: AsyncSession, file_id: UUID) -> str | None:
    """Read file content from the project's GitHub fork.

    Returns the file content as a string, or None if the file or project
    is not found.
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

    try:
        repo = github_service.parse_repo(project.fork_repo)
        content, _sha = await github_service.get_file_content(
            repo, tracked_file.file_path, project.fork_branch
        )
        return content
    except github_service.GitHubError:
        logger.warning(
            "Could not fetch file %s from GitHub for project %s",
            tracked_file.file_path,
            project.id,
        )
        return None
