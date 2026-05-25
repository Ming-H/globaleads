"""
B2B Tasks API tests.

Tests for:
- POST /api/v1/b2b-tasks - create B2B task
- GET /api/v1/b2b-tasks - list tasks with pagination
- GET /api/v1/b2b-tasks/{id} - get task details
- POST /api/v1/b2b-tasks/{id}/stop - stop running task
- POST /api/v1/b2b-tasks/{id}/retry - retry failed task
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_b2b_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_user,
    mock_b2b_celery_delay,
):
    """Test creating a B2B task with valid data."""
    response = await test_client.post(
        "/api/v1/b2b-tasks",
        json={
            "name": "Test B2B Task",
            "industry": "Technology",
            "region": "United States",
            "company_size": "11-50",
            "data_sources": ["google_search", "osm"],
            "max_results": 100,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test B2B Task"
    assert data["industry"] == "Technology"
    assert data["region"] == "United States"
    assert data["company_size"] == "11-50"
    assert data["data_sources"] == ["google_search", "osm"]
    assert data["max_results"] == 100
    assert data["status"] == "running"
    assert data["lead_count"] == 0
    assert "id" in data
    assert "celery_task_id" in data
    assert mock_b2b_celery_delay.called


@pytest.mark.asyncio
async def test_create_b2b_task_minimal_data(
    test_client: AsyncClient,
    auth_headers: dict,
    mock_b2b_celery_delay,
):
    """Test creating a B2B task with minimal required data."""
    response = await test_client.post(
        "/api/v1/b2b-tasks",
        json={
            "name": "Minimal Task",
            "data_sources": ["osm"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Task"
    assert data["data_sources"] == ["osm"]


@pytest.mark.asyncio
async def test_create_b2b_task_missing_required_field(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a B2B task without required fields returns 422."""
    response = await test_client.post(
        "/api/v1/b2b-tasks",
        json={
            "name": "Test Task",
            # data_sources missing
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_b2b_task_empty_data_sources(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a B2B task with empty data_sources returns 422."""
    response = await test_client.post(
        "/api/v1/b2b-tasks",
        json={
            "name": "Test Task",
            "data_sources": [],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_b2b_task_multiple_sources(
    test_client: AsyncClient,
    auth_headers: dict,
    mock_b2b_celery_delay,
):
    """Test creating a B2B task with multiple data sources."""
    response = await test_client.post(
        "/api/v1/b2b-tasks",
        json={
            "name": "Multi Source Task",
            "industry": "Manufacturing",
            "region": "Europe",
            "data_sources": ["google_search", "osm"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert set(data["data_sources"]) == {"google_search", "osm"}


@pytest.mark.asyncio
async def test_list_b2b_tasks_empty(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test listing B2B tasks when none exist."""
    response = await test_client.get(
        "/api/v1/b2b-tasks",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_b2b_tasks_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_task,
):
    """Test listing B2B tasks returns user's tasks."""
    response = await test_client.get(
        "/api/v1/b2b-tasks",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == test_b2b_task.id
    assert data["items"][0]["name"] == test_b2b_task.name


@pytest.mark.asyncio
async def test_list_b2b_tasks_with_status_filter(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
):
    """Test listing B2B tasks filtered by status."""
    from app.models.b2b_task import B2BTask

    # Create tasks with different statuses
    for status in ["pending", "running", "completed"]:
        task = B2BTask(
            user_id=test_user.id,
            name=f"{status.title()} Task",
            data_sources=["google_search", "osm"],
            status=status,
            lead_count=0,
        )
        test_session.add(task)
    await test_session.commit()

    response = await test_client.get(
        "/api/v1/b2b-tasks?status_filter=completed",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for task in data["items"]:
        assert task["status"] == "completed"


@pytest.mark.asyncio
async def test_list_b2b_tasks_with_pagination(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
):
    """Test listing B2B tasks with pagination."""
    from app.models.b2b_task import B2BTask

    # Create multiple tasks
    for i in range(5):
        task = B2BTask(
            user_id=test_user.id,
            name=f"Task {i}",
            data_sources=["google_search", "osm"],
            status="pending",
            lead_count=0,
        )
        test_session.add(task)
    await test_session.commit()

    # Get first page
    response = await test_client.get(
        "/api/v1/b2b-tasks?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_b2b_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_task,
):
    """Test getting a specific B2B task by ID."""
    response = await test_client.get(
        f"/api/v1/b2b-tasks/{test_b2b_task.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_b2b_task.id
    assert data["name"] == test_b2b_task.name
    assert data["industry"] == test_b2b_task.industry


@pytest.mark.asyncio
async def test_get_b2b_task_not_found(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting a non-existent B2B task returns 404."""
    response = await test_client.get(
        "/api/v1/b2b-tasks/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_b2b_task_unauthorized(
    test_client: AsyncClient,
    test_session,
    test_b2b_task,
):
    """Test getting another user's task returns 404."""
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
        f"/api/v1/b2b-tasks/{test_b2b_task.id}",
        headers=other_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stop_b2b_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    mock_celery_app_control_revoke,
):
    """Test stopping a running B2B task."""
    from app.models.b2b_task import B2BTask

    task = B2BTask(
        user_id=test_user.id,
        name="Running Task",
        data_sources=["google_search", "osm"],
        status="running",
        celery_task_id="celery-task-123",
        lead_count=0,
    )
    test_session.add(task)
    await test_session.commit()

    response = await test_client.post(
        f"/api/v1/b2b-tasks/{task.id}/stop",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务已停止"
    assert data["task_id"] == task.id
    assert mock_celery_app_control_revoke.called


@pytest.mark.asyncio
async def test_stop_b2b_task_not_running(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_task,
):
    """Test stopping a task that is not running returns 400."""
    response = await test_client.post(
        f"/api/v1/b2b-tasks/{test_b2b_task.id}/stop",
        headers=auth_headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_retry_b2b_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    mock_b2b_celery_delay,
):
    """Test retrying a failed B2B task."""
    from app.models.b2b_task import B2BTask

    task = B2BTask(
        user_id=test_user.id,
        name="Failed Task",
        data_sources=["google_search", "osm"],
        status="failed",
        error_message="API rate limit exceeded",
        lead_count=0,
    )
    test_session.add(task)
    await test_session.commit()

    response = await test_client.post(
        f"/api/v1/b2b-tasks/{task.id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务已重新开始"
    assert data["task_id"] == task.id
    assert mock_b2b_celery_delay.called


@pytest.mark.asyncio
async def test_retry_b2b_task_quota_exceeded(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    mock_b2b_celery_delay,
):
    """Test retrying a task with quota_exceeded status."""
    from app.models.b2b_task import B2BTask

    task = B2BTask(
        user_id=test_user.id,
        name="Quota Exceeded Task",
        data_sources=["google_search", "osm"],
        status="quota_exceeded",
        error_message="API quota exceeded",
        lead_count=0,
    )
    test_session.add(task)
    await test_session.commit()

    response = await test_client.post(
        f"/api/v1/b2b-tasks/{task.id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务已重新开始"


@pytest.mark.asyncio
async def test_retry_b2b_task_not_failed(
    test_client: AsyncClient,
    auth_headers: dict,
    test_b2b_task,
):
    """Test retrying a task that didn't fail returns 400."""
    response = await test_client.post(
        f"/api/v1/b2b-tasks/{test_b2b_task.id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 400
