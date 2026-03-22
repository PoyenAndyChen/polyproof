from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.agent import AuthorResponse
from app.schemas.comment import CommentThread


class ConjectureSummary(BaseModel):
    """Minimal conjecture shape used in parent_chain, children, proved_siblings."""

    id: UUID
    lean_statement: str
    description: str
    status: str
    proof_lean: str | None = None
    proved_by: AuthorResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ConjectureResponse(BaseModel):
    """Conjecture in list views."""

    id: UUID
    project_id: UUID
    parent_id: UUID | None = None
    lean_statement: str
    description: str
    status: str
    priority: str
    proved_by: AuthorResponse | None = None
    disproved_by: AuthorResponse | None = None
    comment_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConjectureListResponse(BaseModel):
    conjectures: list[ConjectureResponse]
    total: int


class ChildSummary(BaseModel):
    """Minimal child info for the decomposed conjecture hint."""

    id: UUID
    status: str
    description: str


class ConjectureDetail(BaseModel):
    """Full conjecture context for detail page."""

    id: UUID
    project_id: UUID
    parent_id: UUID | None = None
    lean_statement: str
    description: str
    status: str
    priority: str
    sorry_proof: str | None = None
    proof_lean: str | None = None
    proved_by: AuthorResponse | None = None
    disproved_by: AuthorResponse | None = None
    comment_count: int = 0
    created_at: datetime
    closed_at: datetime | None = None
    parent_chain: list[ConjectureSummary] = []
    proved_siblings: list[ConjectureSummary] = []
    children: list[ConjectureSummary] = []
    comments: CommentThread | None = None
    hint: str | None = None
    children_summary: list[ChildSummary] | None = None

    model_config = ConfigDict(from_attributes=True)
