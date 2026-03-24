from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import AuthorResponse


class SorrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    declaration_name: str
    sorry_index: int
    goal_state: str
    status: str
    priority: str
    filled_by_handle: str | None = None


class SorryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_id: UUID
    project_id: UUID
    declaration_name: str
    sorry_index: int
    goal_state: str
    local_context: str | None = None
    status: str
    priority: str
    active_agents: int = 0
    filled_by: AuthorResponse | None = None
    fill_tactics: str | None = None
    fill_description: str | None = None
    filled_at: datetime | None = None
    parent_sorry_id: UUID | None = None
    file_path: str = ""
    comment_count: int = 0
    line: int | None = None
    col: int | None = None
    created_at: datetime


class SorryDetail(SorryResponse):
    children: list[SorrySummary] = []
    parent_chain: list[SorrySummary] = []
    comments: CommentThread | None = None


class SorryListResponse(BaseModel):
    sorries: list[SorryResponse]
    total: int


class FillRequest(BaseModel):
    tactics: str = Field(min_length=1, max_length=100000)
    description: str = Field(min_length=20, max_length=5000)


class FillResponse(BaseModel):
    status: str  # queued, error
    job_id: UUID | None = None
    error: str | None = None


from app.schemas.comment import CommentThread  # noqa: E402

SorryDetail.model_rebuild()
