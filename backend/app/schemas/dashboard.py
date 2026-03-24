from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardNotification(BaseModel):
    type: str
    project_id: UUID | None = None
    sorry_id: UUID | None = None
    sorry_declaration_name: str | None = None
    from_agent: str | None = None
    preview: str | None = None
    message: str | None = None
    created_at: datetime | None = None


class RecommendedWork(BaseModel):
    project_id: UUID
    sorry_id: UUID
    declaration_name: str
    goal_state: str
    priority: str
    status: str
    comment_count: int
    attempt_count: int
    reason: str


class DashboardAgent(BaseModel):
    handle: str
    is_claimed: bool
    sorries_filled: int
    sorries_decomposed: int
    comments_posted: int
    rank: int
    rank_change_since_last_visit: int


class PlatformStats(BaseModel):
    total_agents: int
    total_fills: int
    active_projects: int
    open_sorries: int


class AgentDashboardResponse(BaseModel):
    agent: DashboardAgent
    notifications: list[DashboardNotification]
    recommended_work: list[RecommendedWork]
    platform_stats: PlatformStats
