from uuid import UUID

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    lean_code: str = Field(..., min_length=1)
    conjecture_id: UUID | None = None


class VerifyResult(BaseModel):
    status: str
    error: str | None = None
