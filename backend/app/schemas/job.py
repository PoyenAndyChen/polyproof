from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    sorry_id: UUID | None = None
    agent_id: UUID | None = None
    job_type: str
    status: str  # queued, compiling, merged, failed, superseded
    lean_output: str | None = None
    result: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None
