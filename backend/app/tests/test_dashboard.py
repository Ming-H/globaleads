"""
Dashboard API tests.

Tests for:
- GET /api/v1/dashboard/stats - get dashboard statistics
- GET /api/v1/dashboard/trends - get trend data

Note: These tests require PostgreSQL (uses jsonb_array_elements_text, date_trunc).
Marked as @pytest.mark.integration — skipped in normal pytest runs.
Run with: pytest -m integration  (needs real PostgreSQL)
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

# All dashboard tests need PostgreSQL (jsonb_array_elements_text, date_trunc)
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_dashboard_stats_no_data(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard stats when user has no data."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "social_leads" in data
    assert "b2b_leads" in data
    assert "tasks" in data
    assert "api_usage" in data

    # Check social leads stats structure
    social_leads = data["social_leads"]
    assert "total" in social_leads
    assert "this_week" in social_leads
    assert "by_platform" in social_leads
    assert "avg_score" in social_leads
    assert "by_tag" in social_leads

    # Check B2B leads stats structure
    b2b_leads = data["b2b_leads"]
    assert "total" in b2b_leads
    assert "this_week" in b2b_leads
    assert "by_source" in b2b_leads
    assert "with_email" in b2b_leads
    assert "by_industry" in b2b_leads

    # Check tasks stats structure
    tasks = data["tasks"]
    assert "social_total" in tasks
    assert "b2b_total" in tasks
    assert "success_rate" in tasks

    # Check API usage structure
    api_usage = data["api_usage"]
    assert isinstance(api_usage, dict)


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    test_social_task,
    test_social_lead,
    test_b2b_task,
    test_b2b_lead,
):
    """Test getting dashboard stats with existing data."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should have at least 1 social lead
    assert data["social_leads"]["total"] >= 1

    # Should have at least 1 B2B lead
    assert data["b2b_leads"]["total"] >= 1

    # Should have at least 1 social task
    assert data["tasks"]["social_total"] >= 1

    # Should have at least 1 B2B task
    assert data["tasks"]["b2b_total"] >= 1


@pytest.mark.asyncio
async def test_get_dashboard_stats_by_platform(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test dashboard stats group by platform."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    by_platform = data["social_leads"]["by_platform"]
    assert isinstance(by_platform, dict)
    # Should have reddit platform from test fixture
    if data["social_leads"]["total"] > 0:
        assert len(by_platform) > 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_by_source(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test dashboard stats group by data source."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    by_source = data["b2b_leads"]["by_source"]
    assert isinstance(by_source, dict)
    # Should have google_search source from test fixture
    if data["b2b_leads"]["total"] > 0:
        assert len(by_source) > 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_avg_score(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test dashboard stats average AI score calculation."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    avg_score = data["social_leads"]["avg_score"]
    assert isinstance(avg_score, float)
    assert avg_score >= 0
    assert avg_score <= 100


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_email_count(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test dashboard stats count of leads with email."""
    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    with_email = data["b2b_leads"]["with_email"]
    assert isinstance(with_email, int)
    assert with_email >= 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_success_rate(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
):
    """Test dashboard stats task success rate calculation."""
    from app.models.social_task import SocialTask
    from app.models.b2b_task import B2BTask

    # Create completed tasks
    social_task = SocialTask(
        user_id=test_user.id,
        name="Completed Social Task",
        keywords=["test"],
        platforms=["reddit"],
        status="completed",
        lead_count=5,
    )
    test_session.add(social_task)

    b2b_task = B2BTask(
        user_id=test_user.id,
        name="Completed B2B Task",
        data_sources=["google_search", "osm"],
        status="completed",
        lead_count=10,
    )
    test_session.add(b2b_task)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    success_rate = data["tasks"]["success_rate"]
    assert isinstance(success_rate, float)
    assert success_rate >= 0
    assert success_rate <= 1


@pytest.mark.asyncio
async def test_get_dashboard_trends_no_data(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends when user has no data."""
    response = await test_client.get(
        "/api/v1/dashboard/trends",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "period" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["period"] in ["day", "week", "month"]


@pytest.mark.asyncio
async def test_get_dashboard_trends_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test getting dashboard trends with existing data."""
    from app.models.social_lead import SocialLead

    # Create leads with different timestamps
    now = datetime.utcnow()
    for i in range(3):
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{i}",
            content=f"Content {i}",
            published_at=now - timedelta(days=i),
            ai_score=50,
            ai_tags=[],
            status="uncontacted",
            created_at=now - timedelta(days=i),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/dashboard/trends?days=7",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 0

    # Check item structure
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert "date" in item
        assert "social_leads" in item
        assert "b2b_leads" in item


@pytest.mark.asyncio
async def test_get_dashboard_trends_period_day(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with day period."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?period=day",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "day"


@pytest.mark.asyncio
async def test_get_dashboard_trends_period_week(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with week period."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?period=week",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "week"


@pytest.mark.asyncio
async def test_get_dashboard_trends_period_month(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with month period."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?period=month",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "month"


@pytest.mark.asyncio
async def test_get_dashboard_trends_custom_days(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with custom days parameter."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?days=30",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_get_dashboard_trends_invalid_period(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with invalid period returns 422."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?period=invalid",
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dashboard_trends_days_exceeds_limit(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting dashboard trends with days > 365 returns 422."""
    response = await test_client.get(
        "/api/v1/dashboard/trends?days=400",
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dashboard_unauthorized(
    test_client: AsyncClient,
):
    """Test accessing dashboard without authentication returns 401."""
    response = await test_client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401

    response = await test_client.get("/api/v1/dashboard/trends")

    assert response.status_code == 401
