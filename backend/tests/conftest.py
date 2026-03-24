import hashlib
import os
import secrets
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.connection import Base
from app.main import app
from app.models.agent import Agent
from app.models.project import Project
from app.models.sorry import Sorry
from app.models.tracked_file import TrackedFile

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://andy@localhost:5432/polyproof_test",
)


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.execute(sa_text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(sa_text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.execute(sa_text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(sa_text("CREATE SCHEMA public"))
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_agent(db_session: AsyncSession) -> dict:
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(
        id=uuid4(),
        handle="test_agent_" + secrets.token_hex(4),
        type="community",
        api_key_hash=key_hash,
    )
    db_session.add(agent)
    await db_session.flush()
    return {"agent": agent, "api_key": raw_key}


@pytest.fixture
async def seed_mega_agent(db_session: AsyncSession) -> dict:
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(
        id=uuid4(),
        handle="mega_agent_" + secrets.token_hex(4),
        type="mega",
        api_key_hash=key_hash,
    )
    db_session.add(agent)
    await db_session.flush()
    return {"agent": agent, "api_key": raw_key}


@pytest.fixture
async def seed_project(db_session: AsyncSession) -> dict:
    """Create a project with a tracked file and some sorry's."""
    import hashlib as hl
    project_id = uuid4()
    file_id = uuid4()
    sorry_ids = [uuid4() for _ in range(3)]

    project = Project(
        id=project_id,
        title="Test Project: Carleson",
        description="A test project for unit tests.",
        upstream_repo="https://github.com/fpvandoorn/carleson",
        upstream_branch="master",
        fork_repo="https://github.com/polyproof/carleson",
        fork_branch="polyproof",
        lean_toolchain="leanprover/lean4:v4.28.0",
        workspace_path="/opt/polyproof/projects/carleson",
    )
    db_session.add(project)
    await db_session.flush()

    tracked_file = TrackedFile(
        id=file_id,
        project_id=project_id,
        file_path="Carleson/ToMathlib/Analysis/TriangleInequality.lean",
        sorry_count=3,
    )
    db_session.add(tracked_file)
    await db_session.flush()

    sorries = []
    for i, sid in enumerate(sorry_ids):
        goal = f"⊢ test_goal_{i} = true"
        s = Sorry(
            id=sid,
            file_id=file_id,
            project_id=project_id,
            declaration_name=f"test_theorem_{i}",
            sorry_index=0,
            goal_state=goal,
            local_context=f"h : test_hyp_{i}",
            goal_hash=hl.sha256(goal.encode()).hexdigest()[:16],
            status="open",
            priority="normal",
        )
        sorries.append(s)
        db_session.add(s)
    await db_session.flush()

    return {
        "project": project,
        "tracked_file": tracked_file,
        "sorries": sorries,
    }


@pytest.fixture
def auth_headers(seed_agent: dict) -> dict:
    return {"Authorization": f"Bearer {seed_agent['api_key']}"}


@pytest.fixture
def mega_auth_headers(seed_mega_agent: dict) -> dict:
    return {"Authorization": f"Bearer {seed_mega_agent['api_key']}"}


@pytest.fixture
def mock_lean_pass(monkeypatch):
    from app.services.lean_client import LeanResult

    async def _mock(*args, **kwargs):
        return LeanResult(status="passed", error=None)

    monkeypatch.setattr("app.services.lean_client.typecheck", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_in_file", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_freeform", _mock, raising=False)


@pytest.fixture
def mock_lean_fail(monkeypatch):
    from app.services.lean_client import LeanResult

    async def _mock(*args, **kwargs):
        return LeanResult(status="rejected", error="type mismatch")

    monkeypatch.setattr("app.services.lean_client.typecheck", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_in_file", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_freeform", _mock, raising=False)
