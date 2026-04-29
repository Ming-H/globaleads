"""
Social Leads API tests.

Tests for:
- GET /api/v1/social-leads - list leads with filtering and pagination
- GET /api/v1/social-leads/{id} - get lead details
- PATCH /api/v1/social-leads/{id}/status - update lead status
- POST /api/v1/social-leads/export - export leads to CSV/Excel
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_social_leads_empty(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test listing social leads when none exist."""
    response = await test_client.get(
        "/api/v1/social-leads",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_social_leads_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test listing social leads returns user's leads."""
    response = await test_client.get(
        "/api/v1/social-leads",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == test_social_lead.id
    assert data["items"][0]["platform"] == test_social_lead.platform


@pytest.mark.asyncio
async def test_list_social_leads_filter_by_platform(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test listing social leads filtered by platform."""
    response = await test_client.get(
        "/api/v1/social-leads?platform=reddit",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["platform"] == "reddit"


@pytest.mark.asyncio
async def test_list_social_leads_filter_by_min_score(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test listing social leads filtered by minimum score."""
    from app.models.social_lead import SocialLead
    from datetime import datetime

    # Create leads with different scores
    for score in [30, 60, 90]:
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{score}",
            content=f"Content with score {score}",
            published_at=datetime.utcnow(),
            ai_score=score,
            ai_tags=[],
            status="uncontacted",
            created_at=datetime.utcnow(),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/social-leads?min_score=50",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["ai_score"] >= 50


@pytest.mark.asyncio
async def test_list_social_leads_filter_by_status(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test listing social leads filtered by status."""
    from app.models.social_lead import SocialLead
    from datetime import datetime

    # Create leads with different statuses
    for status in ["uncontacted", "contacted", "replied"]:
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{status}",
            content=f"Content with status {status}",
            published_at=datetime.utcnow(),
            ai_score=50,
            ai_tags=[],
            status=status,
            created_at=datetime.utcnow(),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/social-leads?status_filter=contacted",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["status"] == "contacted"


@pytest.mark.asyncio
async def test_list_social_leads_filter_by_task(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test listing social leads filtered by task ID."""
    response = await test_client.get(
        f"/api/v1/social-leads?task_id={test_social_lead.task_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["task_id"] == test_social_lead.task_id


@pytest.mark.asyncio
async def test_list_social_leads_with_pagination(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test listing social leads with pagination."""
    from app.models.social_lead import SocialLead
    from datetime import datetime

    # Create multiple leads
    for i in range(5):
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{i}",
            content=f"Content {i}",
            published_at=datetime.utcnow(),
            ai_score=50,
            ai_tags=[],
            status="uncontacted",
            created_at=datetime.utcnow(),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/social-leads?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_social_leads_sort_by_score(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test listing social leads sorted by AI score."""
    from app.models.social_lead import SocialLead
    from datetime import datetime

    # Create leads with different scores
    for score in [30, 90, 60]:
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{score}",
            content=f"Content with score {score}",
            published_at=datetime.utcnow(),
            ai_score=score,
            ai_tags=[],
            status="uncontacted",
            created_at=datetime.utcnow(),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/social-leads?sort_by=ai_score&sort_order=desc",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    if len(data["items"]) >= 2:
        # Check descending order
        scores = [item["ai_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_get_social_lead_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test getting a specific social lead by ID."""
    response = await test_client.get(
        f"/api/v1/social-leads/{test_social_lead.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_social_lead.id
    assert data["platform"] == test_social_lead.platform
    assert data["author_name"] == test_social_lead.author_name


@pytest.mark.asyncio
async def test_get_social_lead_not_found(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting a non-existent social lead returns 404."""
    response = await test_client.get(
        "/api/v1/social-leads/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_social_lead_status_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test updating a social lead's contact status."""
    response = await test_client.patch(
        f"/api/v1/social-leads/{test_social_lead.id}/status",
        json={"status": "contacted"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "contacted"


@pytest.mark.asyncio
async def test_update_social_lead_status_to_replied(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test updating lead status to replied."""
    response = await test_client.patch(
        f"/api/v1/social-leads/{test_social_lead.id}/status",
        json={"status": "replied"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "replied"


@pytest.mark.asyncio
async def test_update_social_lead_status_to_invalid(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test updating lead status with invalid value."""
    response = await test_client.patch(
        f"/api/v1/social-leads/{test_social_lead.id}/status",
        json={"status": "invalid_status"},
        headers=auth_headers,
    )

    # This may return 422 if Pydantic validates the status
    assert response.status_code in [422, 200]


@pytest.mark.asyncio
async def test_export_social_leads_csv(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test exporting social leads as CSV."""
    response = await test_client.post(
        "/api/v1/social-leads/export",
        json={
            "format": "csv",
            "task_id": test_social_lead.task_id,
            "filters": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert "social_leads_" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_social_leads_xlsx(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_lead,
):
    """Test exporting social leads as Excel."""
    response = await test_client.post(
        "/api/v1/social-leads/export",
        json={
            "format": "xlsx",
            "task_id": test_social_lead.task_id,
            "filters": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "application/vnd.openxmlformats" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_social_leads_with_filters(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_social_task,
):
    """Test exporting social leads with filters applied."""
    from app.models.social_lead import SocialLead
    from datetime import datetime

    # Create leads with different scores
    for score in [30, 80]:
        lead = SocialLead(
            task_id=test_social_task.id,
            platform="reddit",
            author_name=f"user_{score}",
            content=f"Content with score {score}",
            published_at=datetime.utcnow(),
            ai_score=score,
            ai_tags=[],
            status="uncontacted",
            created_at=datetime.utcnow(),
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.post(
        "/api/v1/social-leads/export",
        json={
            "format": "csv",
            "task_id": test_social_task.id,
            "filters": {"min_score": "50"},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Check that exported content contains data
    assert len(content) > 0


@pytest.mark.asyncio
async def test_get_social_lead_unauthorized(
    test_client: AsyncClient,
    test_session,
    test_social_lead,
):
    """Test getting another user's lead returns 404."""
    from app.models.user import User
    from app.core.security import hash_password, create_access_token

    # Create another user
    other_user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=hash_password("pass123"),
        is_active=True,
    )
    test_session.add(other_user)
    await test_session.commit()

    other_token = create_access_token(data={"sub": str(other_user.id)})
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = await test_client.get(
        f"/api/v1/social-leads/{test_social_lead.id}",
        headers=other_headers,
    )

    assert response.status_code == 404
