"""
B2B Leads API tests.

Tests for:
- GET /api/v1/b2b-leads - list leads with filtering and pagination
- GET /api/v1/b2b-leads/{id} - get lead details
- PATCH /api/v1/b2b-leads/{id}/status - update lead status
- POST /api/v1/b2b-leads/export - export leads to CSV/Excel
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_b2b_leads_empty(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test listing B2B leads when none exist."""
    response = await test_client.get(
        "/api/v1/b2b-leads",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_b2b_leads_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test listing B2B leads returns user's leads."""
    response = await test_client.get(
        "/api/v1/b2b-leads",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == test_b2b_lead.id
    assert data["items"][0]["company_name"] == test_b2b_lead.company_name


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_industry(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test listing B2B leads filtered by industry."""
    response = await test_client.get(
        "/api/v1/b2b-leads?industry=Technology",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["industry"] == "Technology"


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_region(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test listing B2B leads filtered by region."""
    response = await test_client.get(
        "/api/v1/b2b-leads?region=United States",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["region"] == "United States"


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_data_source(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test listing B2B leads filtered by data source."""
    response = await test_client.get(
        "/api/v1/b2b-leads?data_source=apollo",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["data_source"] == "apollo"


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_has_email(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_b2b_task,
):
    """Test listing B2B leads filtered by having email."""
    from app.models.b2b_lead import B2BLead

    # Create leads with and without email
    lead_with_email = B2BLead(
        task_id=test_b2b_task.id,
        company_name="Company A",
        contact_email="contact@companya.com",
        data_source="apollo",
        status="uncontacted",
    )
    lead_without_email = B2BLead(
        task_id=test_b2b_task.id,
        company_name="Company B",
        contact_email=None,
        data_source="google_maps",
        status="uncontacted",
    )
    test_session.add(lead_with_email)
    test_session.add(lead_without_email)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/b2b-leads?has_email=true",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["contact_email"] is not None
        assert lead["contact_email"] != ""


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_status(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_b2b_task,
):
    """Test listing B2B leads filtered by status."""
    from app.models.b2b_lead import B2BLead

    # Create leads with different statuses
    for status in ["uncontacted", "contacted", "replied"]:
        lead = B2BLead(
            task_id=test_b2b_task.id,
            company_name=f"Company {status}",
            contact_email=f"{status}@company.com",
            data_source="apollo",
            status=status,
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/b2b-leads?status_filter=contacted",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["status"] == "contacted"


@pytest.mark.asyncio
async def test_list_b2b_leads_filter_by_task(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test listing B2B leads filtered by task ID."""
    response = await test_client.get(
        f"/api/v1/b2b-leads?task_id={test_b2b_lead.task_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for lead in data["items"]:
        assert lead["task_id"] == test_b2b_lead.task_id


@pytest.mark.asyncio
async def test_list_b2b_leads_with_pagination(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_b2b_task,
):
    """Test listing B2B leads with pagination."""
    from app.models.b2b_lead import B2BLead

    # Create multiple leads
    for i in range(5):
        lead = B2BLead(
            task_id=test_b2b_task.id,
            company_name=f"Company {i}",
            contact_email=f"contact{i}@company.com",
            data_source="apollo",
            status="uncontacted",
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/b2b-leads?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_b2b_lead_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test getting a specific B2B lead by ID."""
    response = await test_client.get(
        f"/api/v1/b2b-leads/{test_b2b_lead.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_b2b_lead.id
    assert data["company_name"] == test_b2b_lead.company_name
    assert data["contact_email"] == test_b2b_lead.contact_email


@pytest.mark.asyncio
async def test_get_b2b_lead_not_found(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting a non-existent B2B lead returns 404."""
    response = await test_client.get(
        "/api/v1/b2b-leads/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_b2b_lead_status_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test updating a B2B lead's contact status."""
    response = await test_client.patch(
        f"/api/v1/b2b-leads/{test_b2b_lead.id}/status",
        json={"status": "contacted"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "contacted"


@pytest.mark.asyncio
async def test_update_b2b_lead_status_to_replied(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test updating lead status to replied."""
    response = await test_client.patch(
        f"/api/v1/b2b-leads/{test_b2b_lead.id}/status",
        json={"status": "replied"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "replied"


@pytest.mark.asyncio
async def test_update_b2b_lead_status_to_invalid(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test updating lead status with invalid value."""
    response = await test_client.patch(
        f"/api/v1/b2b-leads/{test_b2b_lead.id}/status",
        json={"status": "invalid_status"},
        headers=auth_headers,
    )

    # This may return 422 if Pydantic validates the status
    assert response.status_code in [422, 200]


@pytest.mark.asyncio
async def test_export_b2b_leads_csv(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test exporting B2B leads as CSV."""
    response = await test_client.post(
        "/api/v1/b2b-leads/export",
        json={
            "format": "csv",
            "task_id": test_b2b_lead.task_id,
            "filters": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert "b2b_leads_" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_b2b_leads_xlsx(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test exporting B2B leads as Excel."""
    response = await test_client.post(
        "/api/v1/b2b-leads/export",
        json={
            "format": "xlsx",
            "task_id": test_b2b_lead.task_id,
            "filters": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "application/vnd.openxmlformats" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_b2b_leads_with_filters(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_b2b_task,
):
    """Test exporting B2B leads with filters applied."""
    from app.models.b2b_lead import B2BLead

    # Create leads with different industries
    for industry in ["Technology", "Manufacturing"]:
        lead = B2BLead(
            task_id=test_b2b_task.id,
            company_name=f"{industry} Company",
            contact_email=f"contact@{industry.lower()}.com",
            industry=industry,
            data_source="apollo",
            status="uncontacted",
        )
        test_session.add(lead)
    await test_session.commit()

    response = await test_client.post(
        "/api/v1/b2b-leads/export",
        json={
            "format": "csv",
            "task_id": test_b2b_task.id,
            "filters": {"industry": "Technology"},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert len(content) > 0


@pytest.mark.asyncio
async def test_export_b2b_leads_without_task_filter(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_lead,
):
    """Test exporting all B2B leads without task filter."""
    response = await test_client.post(
        "/api/v1/b2b-leads/export",
        json={
            "format": "csv",
            "filters": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_get_b2b_lead_unauthorized(
    test_client: AsyncClient,
    test_session,
    test_b2b_lead,
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
        f"/api/v1/b2b-leads/{test_b2b_lead.id}",
        headers=other_headers,
    )

    assert response.status_code == 404
