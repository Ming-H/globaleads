"""
Test fixtures and configuration for pytest.

Uses SQLite in-memory database for isolated testing.
"""
import asyncio
import os
import sys
import pytest
import pytest_asyncio
import tempfile
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock, patch

# Set test environment before importing app modules
os.environ["ENV_FILE"] = ".env.test"
# Set up a temporary log directory for tests to avoid permission errors
os.environ["LOG_DIR"] = tempfile.gettempdir()

# CRITICAL: Patch JSONB before any SQLAlchemy models are imported
# We need to make JSONB an alias for JSON to work with SQLite
import sqlalchemy
from sqlalchemy import JSON

# Create a fake JSONB that's actually JSON
class FakeJSONB(JSON):
    """Fake JSONB that uses JSON internally for SQLite compatibility."""
    pass

# Replace JSONB in the postgresql dialect module
# This must happen before importing any models
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.JSONB = FakeJSONB

# Also patch it at the module level for imports
sys.modules['sqlalchemy.dialects.postgresql'].JSONB = FakeJSONB

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.security import hash_password, create_access_token
from app.models.base import Base
from app.models.user import User

# Now import models after patching JSONB
from app.models import user, social_task, social_lead, b2b_task, b2b_lead  # noqa: F401

# SQLite in-memory database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """
    Setup test database - create all tables
    This runs once per test session
    """
    async with test_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup after all tests
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.
    Drops and recreates all tables before each test for full isolation.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.close()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_user_token(test_user: User) -> str:
    """Generate a valid JWT token for the test user"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return token


@pytest_asyncio.fixture
async def auth_headers(test_user_token: str) -> dict:
    """Provide authorization headers with valid JWT token"""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async test client for making API calls
    Uses dependency override to inject test database session
    """
    from app.core.database import get_db

    # Override the database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Reset overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, test_user_token: str) -> AsyncClient:
    """Provide a pre-authenticated client for convenience"""
    # Clone client and add default auth headers
    client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return client


# Alias for backward compatibility with existing tests
@pytest_asyncio.fixture
async def test_client(client: AsyncClient) -> AsyncClient:
    """Alias for client fixture for backward compatibility"""
    return client


@pytest.fixture
def mock_celery():
    """Mock Celery task execution"""
    with patch("app.tasks.social_crawl.crawl_social_media.delay") as mock_social, \
         patch("app.tasks.b2b_search.search_b2b_companies.delay") as mock_b2b:

        # Configure mock to return a fake task ID
        mock_result = Mock()
        mock_result.id = "test-celery-task-id-123"
        mock_social.delay.return_value = mock_result
        mock_b2b.delay.return_value = mock_result

        yield {
            "social_crawl": mock_social,
            "b2b_search": mock_b2b,
        }


@pytest.fixture
def mock_social_celery_delay():
    """Mock social Celery task.delay() method"""
    with patch("app.tasks.social_crawl.crawl_social_media.delay") as mock_delay:
        mock_result = Mock()
        mock_result.id = "test-celery-task-id"
        mock_delay.return_value = mock_result
        yield mock_delay


@pytest.fixture
def mock_b2b_celery_delay():
    """Mock B2B Celery task.delay() method"""
    with patch("app.tasks.b2b_search.search_b2b_companies.delay") as mock_delay:
        mock_result = Mock()
        mock_result.id = "test-b2b-celery-task-id"
        mock_delay.return_value = mock_result
        yield mock_delay


@pytest.fixture
def mock_celery_delay():
    """Mock generic Celery task.delay() method for social tasks"""
    with patch("app.tasks.social_crawl.crawl_social_media.delay") as mock_delay:
        mock_result = Mock()
        mock_result.id = "test-celery-task-id"
        mock_delay.return_value = mock_result
        yield mock_delay


@pytest.fixture
def mock_llm_response():
    """Mock LLM API responses for AI service testing"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"has_intent": true, "score": 85, "tags": ["求购", "询价"], "analysis": "用户明确表达购买意向"}'
            }
        }]
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = mock_response
        yield mock_post


@pytest_asyncio.fixture
async def sample_social_task(db_session: AsyncSession, test_user: User) -> social_task.SocialTask:
    """Create a sample social task for testing"""
    task = social_task.SocialTask(
        user_id=test_user.id,
        name="Test Social Task",
        keywords=["LED", "lighting"],
        platforms=["reddit"],
        max_results=100,
        min_score=50,
        status="pending",
        lead_count=0,
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest_asyncio.fixture
async def sample_social_leads(
    db_session: AsyncSession,
    sample_social_task: social_task.SocialTask,
) -> list[social_lead.SocialLead]:
    """Create sample social leads for testing"""
    from datetime import datetime

    now = datetime.utcnow()
    leads = [
        social_lead.SocialLead(
            task_id=sample_social_task.id,
            platform="reddit",
            author_name="user1",
            author_url="https://reddit.com/user/user1",
            content="Looking for LED lighting suppliers, please DM me",
            post_url="https://reddit.com/r/test/post1",
            published_at=datetime.utcnow(),
            ai_score=85,
            ai_tags=["求购", "询价"],
            ai_analysis="用户明确表达购买意向",
            status="uncontacted",
            created_at=now,
        ),
        social_lead.SocialLead(
            task_id=sample_social_task.id,
            platform="reddit",
            author_name="user2",
            author_url="https://reddit.com/user/user2",
            content="Just discussing LED technology trends",
            post_url="https://reddit.com/r/test/post2",
            published_at=datetime.utcnow(),
            ai_score=30,
            ai_tags=["讨论"],
            ai_analysis="只是讨论技术趋势",
            status="uncontacted",
            created_at=now,
        ),
    ]
    for lead in leads:
        db_session.add(lead)
    await db_session.flush()
    return leads


@pytest_asyncio.fixture
async def sample_b2b_task(db_session: AsyncSession, test_user: User) -> b2b_task.B2BTask:
    """Create a sample B2B task for testing"""
    task = b2b_task.B2BTask(
        user_id=test_user.id,
        name="Test B2B Task",
        industry="Lighting",
        region="United States",
        company_size="11-50",
        data_sources=["apollo"],
        max_results=100,
        status="pending",
        lead_count=0,
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest_asyncio.fixture
async def sample_b2b_leads(
    db_session: AsyncSession,
    sample_b2b_task: b2b_task.B2BTask,
) -> list[b2b_lead.B2BLead]:
    """Create sample B2B leads for testing"""
    from datetime import datetime

    now = datetime.utcnow()
    leads = [
        b2b_lead.B2BLead(
            task_id=sample_b2b_task.id,
            company_name="Lighting Corp",
            company_website="https://lightingcorp.com",
            company_size="11-50",
            company_address="123 Main St, New York, NY",
            region="United States",
            industry="Lighting",
            contact_name="John Doe",
            contact_title="Purchasing Manager",
            contact_email="john@lightingcorp.com",
            contact_phone="+1-234-567-8900",
            email_verified=True,
            data_source="apollo",
            source_url="https://apollo.io/lead1",
            status="uncontacted",
            created_at=now,
        ),
        b2b_lead.B2BLead(
            task_id=sample_b2b_task.id,
            company_name="Bright Lights Inc",
            company_website="https://brightlights.com",
            company_size="51-200",
            company_address="456 Oak Ave, Los Angeles, CA",
            region="United States",
            industry="Lighting",
            contact_name="Jane Smith",
            contact_title="CEO",
            contact_email="jane@brightlights.com",
            contact_phone="+1-345-678-9012",
            email_verified=False,
            data_source="google_maps",
            source_url="https://maps.google.com/lead2",
            status="contacted",
            created_at=now,
        ),
    ]
    for lead in leads:
        db_session.add(lead)
    await db_session.flush()
    return leads


@pytest.fixture
def mock_celery_app_control_revoke():
    """Mock Celery app.control.revoke for stop task tests"""
    with patch("app.tasks.celery_app.celery_app.control.revoke") as mock_revoke:
        yield mock_revoke


@pytest.fixture
def mock_celery_delay_for_b2b():
    """Mock B2B Celery task.delay() for retry tests"""
    with patch("app.tasks.b2b_search.search_b2b_companies.delay") as mock_delay:
        mock_result = Mock()
        mock_result.id = "test-b2b-celery-task-id"
        mock_delay.return_value = mock_result
        yield mock_delay


# Aliases — test files reference `test_session` but conftest defines `db_session`
@pytest_asyncio.fixture
async def test_session(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session — many test files reference this name"""
    return db_session


# Aliases for backward compatibility
@pytest_asyncio.fixture
async def test_social_task(sample_social_task) -> social_task.SocialTask:
    """Alias for sample_social_task"""
    return sample_social_task


@pytest_asyncio.fixture
async def test_social_lead(db_session: AsyncSession, sample_social_task: social_task.SocialTask) -> social_lead.SocialLead:
    """Create a single test social lead"""
    from datetime import datetime

    lead = social_lead.SocialLead(
        task_id=sample_social_task.id,
        platform="reddit",
        author_name="test_author",
        author_url="https://reddit.com/user/test_author",
        content="Looking for product recommendations",
        post_url="https://reddit.com/r/test/post/123",
        published_at=datetime.utcnow(),
        ai_score=75,
        ai_tags=["求购"],
        ai_analysis="User wants product recommendations",
        status="uncontacted",
        created_at=datetime.utcnow(),
    )
    db_session.add(lead)
    await db_session.flush()
    await db_session.refresh(lead)
    return lead


@pytest_asyncio.fixture
async def test_b2b_task(sample_b2b_task) -> b2b_task.B2BTask:
    """Alias for sample_b2b_task"""
    return sample_b2b_task


@pytest_asyncio.fixture
async def test_b2b_lead(db_session: AsyncSession, sample_b2b_task: b2b_task.B2BTask) -> b2b_lead.B2BLead:
    """Create a single test B2B lead"""
    from datetime import datetime

    lead = b2b_lead.B2BLead(
        task_id=sample_b2b_task.id,
        company_name="Test Company Inc",
        company_website="https://testcompany.com",
        company_size="11-50",
        company_address="123 Test St, Test City, US",
        region="United States",
        industry="Technology",
        contact_name="John Doe",
        contact_title="CEO",
        contact_email="john@testcompany.com",
        contact_phone="+1234567890",
        email_verified=True,
        data_source="apollo",
        source_url="https://apollo.io/company/test",
        status="uncontacted",
        created_at=datetime.utcnow(),
    )
    db_session.add(lead)
    await db_session.flush()
    await db_session.refresh(lead)
    return lead
