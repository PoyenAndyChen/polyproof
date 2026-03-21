import hashlib
import os
import secrets
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_db
from app.db.connection import Base
from app.main import app
from app.models.agent import Agent
from app.models.conjecture import Conjecture
from app.models.project import Project

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/polyproof_test",
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await trans.rollback()


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
    """Create a community test agent and return dict with agent + raw API key."""
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(
        id=uuid4(),
        handle="test_agent",
        type="community",
        api_key_hash=key_hash,
    )
    db_session.add(agent)
    await db_session.flush()
    return {"agent": agent, "api_key": raw_key}


@pytest.fixture
async def seed_mega_agent(db_session: AsyncSession) -> dict:
    """Create a mega agent and return dict with agent + raw API key."""
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(
        id=uuid4(),
        handle="mega_agent",
        type="mega",
        api_key_hash=key_hash,
    )
    db_session.add(agent)
    await db_session.flush()
    return {"agent": agent, "api_key": raw_key}


@pytest.fixture
async def seed_project(db_session: AsyncSession) -> dict:
    """Create a project with a root conjecture and return both."""
    project_id = uuid4()
    conjecture_id = uuid4()

    project = Project(
        id=project_id,
        title="Test Project",
        description="A test project for unit tests.",
        root_conjecture_id=None,
    )
    db_session.add(project)
    await db_session.flush()

    conjecture = Conjecture(
        id=conjecture_id,
        project_id=project_id,
        parent_id=None,
        lean_statement="∀ n : Nat, n + 0 = n",
        description="Root conjecture for testing.",
        status="open",
        priority="normal",
    )
    db_session.add(conjecture)
    await db_session.flush()

    project.root_conjecture_id = conjecture_id
    await db_session.flush()

    return {"project": project, "root_conjecture": conjecture}


@pytest.fixture
def auth_headers(seed_agent: dict) -> dict:
    return {"Authorization": f"Bearer {seed_agent['api_key']}"}


@pytest.fixture
def mock_lean_pass(monkeypatch):
    """Mock Lean CI to always return pass."""

    async def _mock(*args, **kwargs):
        return {"status": "passed", "error": None}

    monkeypatch.setattr("app.services.lean_client.typecheck", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_proof", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_disproof", _mock, raising=False)


@pytest.fixture
def mock_lean_fail(monkeypatch):
    """Mock Lean CI to always return rejection."""

    async def _mock(*args, **kwargs):
        return {"status": "rejected", "error": "type mismatch"}

    monkeypatch.setattr("app.services.lean_client.typecheck", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_proof", _mock, raising=False)
    monkeypatch.setattr("app.services.lean_client.verify_disproof", _mock, raising=False)
