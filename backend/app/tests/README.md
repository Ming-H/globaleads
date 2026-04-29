# GlobalLeads Backend Test Suite

Complete test suite for the GlobalLeads API using pytest + pytest-asyncio.

## Test Structure

```
app/tests/
├── __init__.py           # Test package initialization
├── conftest.py            # Pytest fixtures and configuration
├── test_auth.py           # Authentication tests
├── test_social_tasks.py   # Social media task tests
├── test_social_leads.py   # Social media lead tests
├── test_b2b_tasks.py      # B2B task tests
├── test_b2b_leads.py      # B2B lead tests
├── test_dashboard.py      # Dashboard tests
└── test_ai_service.py     # AI service tests
```

## Setup

1. **Create test database:**
   ```bash
   createdb globaleads_test
   ```

2. **Install test dependencies:**
   ```bash
   cd backend
   pip install -r requirements-test.txt
   ```

## Running Tests

### Run all tests:
```bash
cd backend
pytest
```

### Run specific test file:
```bash
pytest app/tests/test_auth.py
```

### Run with coverage:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Run with verbose output:
```bash
pytest -v
```

## Test Fixtures

The `conftest.py` provides the following fixtures:

- `db_session`: Async database session (rolled back after each test)
- `test_user`: Test user in the database
- `test_user_token`: Valid JWT token for the test user
- `auth_headers`: Headers with Authorization Bearer token
- `client`: Async test client for API calls
- `authenticated_client`: Pre-authenticated test client
- `mock_celery`: Mocked Celery task execution
- `sample_social_task`: Sample social task for testing
- `sample_social_leads`: Sample social leads for testing
- `sample_b2b_task`: Sample B2B task for testing
- `sample_b2b_leads`: Sample B2B leads for testing

## Test Coverage

### Authentication (test_auth.py) - 178 lines
- Correct username/password login → returns JWT token
- Wrong password login → returns 401
- Non-existent user login → returns 401
- User registration (success/duplicate username/duplicate email)
- Protected endpoint without token → returns 401
- Invalid token → returns 401

### Social Tasks (test_social_tasks.py) - 358 lines
- Create social task (valid parameters)
- Create task missing required fields → returns 422
- Create task empty keywords → returns 422
- Create task invalid max_results → returns 422
- Get task list (empty/with data)
- Get task list with status filter
- Get task list with pagination
- Get single task details
- Get non-existent task → returns 404
- Stop running task
- Stop task not running → returns 400
- Retry failed task
- Retry task not failed → returns 400

### Social Leads (test_social_leads.py) - 438 lines
- Get leads list (empty/with data)
- Filter by platform
- Filter by minimum score
- Filter by status
- Filter by task ID
- Pagination
- Sort by AI score
- Get single lead details
- Get non-existent lead → returns 404
- Update lead status
- Export to CSV
- Export to Excel
- Export with filters
- Unauthorized access → returns 404

### B2B Tasks (test_b2b_tasks.py) - 427 lines
- Create B2B task (valid parameters)
- Create task with minimal data
- Create task missing required fields → returns 422
- Create task empty data_sources → returns 422
- Create task with multiple sources
- Get task list (empty/with data)
- Get task list with status filter
- Get task list with pagination
- Get single task details
- Get non-existent task → returns 404
- Stop running task
- Stop task not running → returns 400
- Retry failed task
- Retry quota_exceeded task
- Retry task not failed → returns 400

### B2B Leads (test_b2b_leads.py) - 447 lines
- Get leads list (empty/with data)
- Filter by industry
- Filter by region
- Filter by data source
- Filter by has_email
- Filter by status
- Filter by task ID
- Pagination
- Get single lead details
- Get non-existent lead → returns 404
- Update lead status
- Export to CSV
- Export to Excel
- Export with filters
- Export without task filter
- Unauthorized access → returns 404

### Dashboard (test_dashboard.py) - 383 lines
- Get stats with no data
- Get stats with existing data
- Stats by platform
- Stats by data source
- Average AI score
- Leads with email count
- Task success rate
- Get trends with no data
- Get trends with data
- Trends period (day/week/month)
- Trends custom days
- Invalid period → returns 422
- Days exceeds limit → returns 422
- Unauthorized access → returns 401

### AI Service (test_ai_service.py) - 335 lines
- Successful AI analysis
- Parse JSON with markdown
- Parse JSON without markdown
- Handle malformed JSON
- Handle HTTP errors
- Score clamping (0-100)
- Batch analysis
- Sync service for Celery
- Partial JSON response
- Timeout handling

## Notes

- Tests use pytest-asyncio for async test support
- Database is cleaned between tests using rollback
- Celery tasks are mocked to avoid actual execution
- External API calls are mocked
- Tests use a separate PostgreSQL test database
- Total test code: ~2,566 lines across 7 test files
