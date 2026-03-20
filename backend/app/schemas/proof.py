from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import AuthorResponse


class ProofCreate(BaseModel):
    lean_proof: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="Lean 4 tactic body (what goes after 'by'). NOT a full program.",
    )
    description: str = Field(
        ...,
        min_length=50,
        max_length=10_000,
        description=(
            "Required. Describe your strategy, result, and insight. "
            "See guidelines.md for templates."
        ),
    )


class ProofResponse(BaseModel):
    id: UUID
    lean_proof: str
    description: str | None
    verification_status: str
    verification_error: str | None
    author: AuthorResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
