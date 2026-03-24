from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.agent import AuthorResponse


class ActivityEventResponse(BaseModel):
    id: UUID
    event_type: str
    sorry_id: UUID | None = None
    sorry_declaration_name: str | None = None
    sorry_goal_state: str | None = None
    agent: AuthorResponse | None = None
    details: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityFeedResponse(BaseModel):
    events: list[ActivityEventResponse]
    total: int
