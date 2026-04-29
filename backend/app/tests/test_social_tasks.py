"""
Social Tasks API tests.

Tests for:
- POST /api/v1/social-tasks - create social task
- GET /api/v1/social-tasks - list tasks with pagination
- GET /api/v1/social-tasks/{id} - get task details
- POST /api/v1/social-tasks/{id}/stop - stop running task
- POST /api/v1/social-tasks/{id}/retry - retry failed task
"""
import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_create_social_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_user,
    mock_celery_delay,
):
    """Test creating a social task with valid data."""
    response = await test_client.post(
        "/api/v1/social-tasks",
        json={
            "name": "Test Task",
            "keywords": ["LED", "lighting"],
            "platforms": ["reddit", "bluesky"],
            "max_results": 100,
            "min_score": 50,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Task"
    assert data["keywords"] == ["LED", "lighting"]
    assert data["platforms"] == ["reddit", "bluesky"]
    assert data["max_results"] == 100
    assert data["min_score"] == 50
    assert data["status"] == "running"
    assert data["lead_count"] == 0
    assert "id" in data
    assert "celery_task_id" in data
    assert mock_celery_delay.called


@pytest.mark.asyncio
async def test_create_social_task_missing_required_field(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a social task without required fields returns 422."""
    response = await test_client.post(
        "/api/v1/social-tasks",
        json={
            "name": "Test Task",
            # keywords missing
            "platforms": ["reddit"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_social_task_empty_keywords(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a social task with empty keywords returns 422."""
    response = await test_client.post(
        "/api/v1/social-tasks",
        json={
            "name": "Test Task",
            "keywords": [],
            "platforms": ["reddit"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_social_task_invalid_max_results(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test creating a social task with invalid max_results returns 422."""
    response = await test_client.post(
        "/api/v1/social-tasks",
        json={
            "name": "Test Task",
            "keywords": ["LED"],
            "platforms": ["reddit"],
            "max_results": 2000,  # exceeds max of 1000
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_social_tasks_empty(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test listing social tasks when none exist."""
    response = await test_client.get(
        "/api/v1/social-tasks",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_social_tasks_with_data(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_task,
):
    """Test listing social tasks returns user's tasks."""
    response = await test_client.get(
        "/api/v1/social-tasks",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == test_social_task.id
    assert data["items"][0]["name"] == test_social_task.name


@pytest.mark.asyncio
async def test_list_social_tasks_with_status_filter(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_task,
):
    """Test listing social tasks filtered by status."""
    response = await test_client.get(
        "/api/v1/social-tasks?status_filter=pending",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for task in data["items"]:
        assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_list_social_tasks_with_pagination(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
):
    """Test listing social tasks with pagination."""
    from app.models.social_task import SocialTask

    # Create multiple tasks
    for i in range(5):
        task = SocialTask(
            user_id=test_user.id,
            name=f"Task {i}",
            keywords=["test"],
            platforms=["reddit"],
            status="pending",
            lead_count=0,
        )
        test_session.add(task)
    await test_session.commit()

    # Get first page
    response = await test_client.get(
        "/api/v1/social-tasks?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_social_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_task,
):
    """Test getting a specific social task by ID."""
    response = await test_client.get(
        f"/api/v1/social-tasks/{test_social_task.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_social_task.id
    assert data["name"] == test_social_task.name


@pytest.mark.asyncio
async def test_get_social_task_not_found(
    test_client: AsyncClient,
    auth_headers: dict,
):
    """Test getting a non-existent social task returns 404."""
    response = await test_client.get(
        "/api/v1/social-tasks/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_social_task_unauthorized(
    test_client: AsyncClient,
    test_session,
    test_social_task,
):
    """Test getting another user's task returns 404."""
    # Create another user
    from app.models.user import User
    from app.core.security import hash_password, create_access_token

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
        f"/api/v1/social-tasks/{test_social_task.id}",
        headers=other_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stop_social_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    mock_celery_app_control_revoke,
):
    """Test stopping a running social task."""
    from app.models.social_task import SocialTask

    task = SocialTask(
        user_id=test_user.id,
        name="Running Task",
        keywords=["test"],
        platforms=["reddit"],
        status="running",
        celery_task_id="celery-task-123",
        lead_count=0,
    )
    test_session.add(task)
    await test_session.commit()

    response = await test_client.post(
        f"/api/v1/social-tasks/{task.id}/stop",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务已停止"
    assert data["task_id"] == task.id
    assert mock_celery_app_control_revoke.called


@pytest.mark.asyncio
async def test_stop_social_task_not_running(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_task,
):
    """Test stopping a task that is not running returns 400."""
    response = await test_client.post(
        f"/api/v1/social-tasks/{test_social_task.id}/stop",
        headers=auth_headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_retry_social_task_success(
    test_client: AsyncClient,
    auth_headers: dict,
    test_session,
    test_user,
    mock_celery_delay,
):
    """Test retrying a failed social task."""
    from app.models.social_task import SocialTask

    task = SocialTask(
        user_id=test_user.id,
        name="Failed Task",
        keywords=["test"],
        platforms=["reddit"],
        status="failed",
        error_message="API rate limit exceeded",
        lead_count=0,
    )
    test_session.add(task)
    await test_session.commit()

    response = await test_client.post(
        f"/api/v1/social-tasks/{task.id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务已重新开始"
    assert data["task_id"] == task.id
    assert mock_celery_delay.called


@pytest.mark.asyncio
async def test_retry_social_task_not_failed(
    test_client: AsyncClient,
    auth_headers: dict,
    test_social_task,
):
    """Test retrying a task that didn't fail returns 400."""
    response = await test_client.post(
        f"/api/v1/social-tasks/{test_social_task.id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 400
