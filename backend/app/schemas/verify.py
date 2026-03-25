from uuid import UUID

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    sorry_id: UUID | None = None
    tactics: str = Field(min_length=1, max_length=100000)


class FreeformVerifyRequest(BaseModel):
    project_id: UUID
    code: str = Field(min_length=1, max_length=100000)


class RemainingGoal(BaseModel):
    line: int
    col: int
    goal: str


class VerifyResult(BaseModel):
    status: str  # passed, rejected, timeout
    error: str | None = None
    sorry_status: str | None = None
    would_be_decomposition: bool = False
    messages: list[dict] | None = None
    remaining_goals: list[RemainingGoal] | None = None
