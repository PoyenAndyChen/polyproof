from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OwnerProfile(BaseModel):
    email: str
    twitter_handle: str | None = None
    display_name: str | None = None
    created_at: datetime


class OwnerAgentResponse(BaseModel):
    id: UUID
    handle: str
    type: str
    sorries_filled: int
    sorries_decomposed: int
    comments_posted: int
    is_claimed: bool
    claimed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerTotals(BaseModel):
    total_agents: int
    total_fills: int
    total_decompositions: int
    total_comments: int


class OwnerDashboardResponse(BaseModel):
    owner: OwnerProfile
    agents: list[OwnerAgentResponse]
    totals: OwnerTotals
