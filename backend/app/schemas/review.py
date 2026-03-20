from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import AuthorResponse


class ReviewCreate(BaseModel):
    verdict: str = Field(..., pattern=r"^(approve|request_changes)$")
    comment: str = Field(..., min_length=50, max_length=10_000)


class ReviewResponse(BaseModel):
    id: UUID
    target_id: UUID
    target_type: str
    reviewer: AuthorResponse
    version: int
    verdict: str
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewList(BaseModel):
    reviews: list[ReviewResponse]
    total: int
