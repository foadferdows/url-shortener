# URL Shortener

A URL shortening service with analytics dashboard built with FastAPI, PostgreSQL, Redis, and Celery.

---

## Tech Stack

| Technology | Role |
|------------|------|
| **FastAPI** | Web framework |
| **PostgreSQL** | Primary database |
| **Redis** | Caching and message broker |
| **Celery** | Background task processing |
| **Docker** | Containerization |

---

## Architecture

The system runs as 4 Docker containers:

| Container | Role | Port |
|-----------|------|------|
| app | FastAPI web server | 8000 |
| db | PostgreSQL database | 5432 |
| redis | Cache & message broker | 6379 |
| celery_worker | Background task processor | — |

---

## Quick Start

```bash
git clone <your-repo>
cd url-shortener
cp .env.example .env        # fill in your values
docker-compose up --build
```

- API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@db:5432/urlshortener` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `SECRET_KEY` | Random secret for security | run: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `BASE_URL` | Base URL of the service | `http://localhost:8000` |
| `CELERY_BROKER_URL` | Celery message broker | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result storage | `redis://redis:6379/2` |
| `DEBUG` | Debug mode | `True` / `False` |

---

## Setup Notes

### Generating a SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ Never commit `.env` to Git. Only `.env.example` should be in version control.



---

## Project Structure

```
url-shortener/
│
├── app/
│   ├── main.py                  # Application entry point
│   ├── database.py              # Database connection and session management
│   ├── api/v1/                  # API endpoints
│   │   ├── auth.py              # Registration, login, API Key
│   │   ├── links.py             # Create/edit/delete links
│   │   ├── analytics.py        # Stats and reports
│   │   ├── dashboard.py        # Overall dashboard stats
│   │   └── middleware.py       # Rate limiting middleware
│   ├── services/                # Business logic
│   │   ├── shortener.py         # Short code generation algorithm
│   │   ├── redirect.py          # Redirect handling
│   │   └── analytics.py        # Visit data collection
│   ├── models/                  # Database table definitions
│   │   ├── user.py              # Users table
│   │   ├── link.py              # Links table
│   │   ├── visit.py             # Visits table
│   │   └── short_code_pool.py   # Pre-generated code pool
│   ├── repositories/            # Database access layer
│   │   ├── link_repo.py
│   │   └── user_repo.py
│   ├── cache/                   # Redis client and helpers
│   │   └── redis_client.py
│   ├── schemas/                 # Response envelope
│   │   └── envelope.py
│   └── workers/                 # Celery background tasks
│       └── tasks.py
│
├── migrations/                  # Database migrations (Alembic)
├── tests/                       # Tests
├── docker-compose.yml
├── Dockerfile
├── .env                         # Local config (not in Git)
├── .env.example                 # Template for config
└── requirements.txt
```

---

## Database Schema

Three main tables:

| Table | Purpose |
|-------|---------|
| `users` | Stores registered users and their API keys |
| `links` | Stores shortened links with metadata |
| `visits` | Stores every click event with visitor info |
| `short_code_pool` | Pre-generated pool of available short codes |

Relationships:
```
User (one) → Links (many) → Visits (many)
```

---

## Short Code Generation — Design Decision

**Chosen approach: Pre-generated Pool**

How it works:
- On startup, 1000 unique 7-character Base62 codes are pre-generated
- Each code is stored in the database with `is_used = false`
- When a user creates a link, a code is atomically claimed from the pool
- When pool drops below 500 codes, it automatically refills to 1000

**Why this approach:**
- Zero latency at link creation time — no generation needed on the fly
- No race conditions — database-level locking (`with_for_update`) prevents duplicate assignment
- Predictable performance under high load

**Trade-offs:**
- Requires extra database table (`short_code_pool`)
- Storage overhead (~1000 rows pre-allocated at all times)
- Slightly more complex than random generation

**Base62 alphabet:** `a-z` + `A-Z` + `0-9` = 62 characters
**Code length:** 7 characters
**Total possible combinations:** 62⁷ = ~3.5 trillion unique codes

---

## API Endpoints

Base URL: `http://localhost:8000`

Authentication: Pass your API key in every request header as `x-api-key`

### Authentication
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register and receive API key | No |

### Links
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/links` | Create a short link | Yes |
| GET | `/api/v1/links` | List all your links | Yes |
| DELETE | `/api/v1/links/{short_code}` | Deactivate a link | Yes |

### Redirect
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/{short_code}` | Redirect to original URL | No |

### Analytics
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/analytics/{short_code}` | Per-link analytics | Yes |
| GET | `/api/v1/analytics` | All links analytics | Yes |
| GET | `/api/v1/analytics/compare` | Multi-link comparison | Yes |

### Dashboard
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/dashboard/stats` | Overall stats for all links | Yes |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Interactive Swagger documentation |

### Example: Create a short link

Request:
```bash
curl -X POST http://localhost:8000/api/v1/links \
  -H "x-api-key: sk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

Response:
```json
{
  "data": {
    "short_code": "aB3kR9x",
    "short_url": "http://localhost:8000/aB3kR9x",
    "original_url": "https://example.com/very/long/url",
    "created_at": "2026-06-06T13:00:00"
  },
  "meta": null,
  "errors": null
}
```

---

## Caching Strategy

**Pattern: Cache-Aside**

On every redirect request:
1. Check Redis first
2. On cache hit → serve directly from Redis (fast path)
3. On cache miss → fetch from DB, store in Redis, then serve

**TTL Policy:**
| Link Type | TTL |
|-----------|-----|
| Regular links | 1 hour |
| Hot links (100+ clicks) | 24 hours |

**Hot Link Detection:**
Links that exceed 100 clicks automatically receive extended TTL in Redis.

**Cache Invalidation:**
When a link is deactivated (deleted), it is immediately removed from Redis
to prevent serving stale data.

**Click Counting — Write-Through:**
Click counts are incremented in Redis first for speed,
then periodically flushed to the database via Celery.

---

## Rate Limiting

**Implementation:** Redis-based counter per IP address or API Key

| User Type | Identifier | Limit | Window |
|-----------|------------|-------|--------|
| Unauthenticated | IP Address | 100 req/min | 60 seconds |
| Authenticated | API Key | 1000 req/min | 60 seconds |

Exceeding the limit returns `HTTP 429 Too Many Requests`.

**Exempt paths:** `/health`, `/docs`, `/openapi.json`

**How it works:**
```
Request arrives
      ↓
Check x-api-key header
      ↓ present              ↓ absent
Use API Key (1000)      Use IP address (100)
      ↓
Redis: INCR rate:{identifier}
       EXPIRE 60s
      ↓
count > limit → 429
count ≤ limit → continue
```

---

## Response Format

All API endpoints return a consistent envelope:

```json
{
  "data": {},
  "meta": null,
  "errors": null
}
```

- `data` — the result payload (object or array)
- `meta` — pagination info or extra context when applicable
- `errors` — error message string on failure, null on success

---

## Pagination

Link listings use cursor-based pagination.

```bash
GET /api/v1/links?cursor=CURSOR&limit=20
```

Response `meta`:
```json
{
  "next_cursor": "2026-06-08T11:14:06.532997",
  "has_more": true,
  "limit": 20
}
```

Pass `next_cursor` as `cursor` in the next request to get the following page. If `has_more` is false, you have reached the end.

**Why cursor-based over offset-based:**
Offset pagination can skip or duplicate items if new data is added mid-session. Cursor pagination anchors to a specific record, so results are always consistent.

---

## Link Features

When creating a link, optional fields are available:

```json
{
  "url": "https://example.com",
  "custom_alias": "my-link",
  "expires_at": "2026-12-31T00:00:00",
  "password": "secret123",
  "webhook_url": "https://your-site.com/webhook",
  "webhook_threshold": 1000
}
```

| Field | Description |
|-------|-------------|
| `custom_alias` | Custom short code instead of auto-generated |
| `expires_at` | Link auto-expires at this datetime |
| `password` | Password gate before redirect (`?password=X`) |
| `webhook_url` | URL to notify when click threshold is reached |
| `webhook_threshold` | Click count that triggers the webhook |

**Lazy Deletion:** Expired links are deactivated on first access rather than by a background cron job. When an expired link is accessed, it is immediately marked inactive and removed from cache.

---

## Analytics

### Analytics Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/analytics/{short_code}` | Per-link analytics | Yes |
| GET | `/api/v1/analytics?days=30` | All links analytics | Yes |
| GET | `/api/v1/analytics/compare?codes=X,Y` | Multi-link comparison | Yes |

### Multi-link Comparison
Compare click trends across multiple links on a single request:

```bash
GET /api/v1/analytics/compare?codes=aB3kR9x,pQ7mN2j&days=30
```

Returns daily visit data for each link side-by-side, suitable for rendering a multi-line chart. Maximum 10 links per request.

```json
{
  "data": [
    {
      "short_code": "aB3kR9x",
      "original_url": "https://example.com",
      "total_clicks": 150,
      "daily_visits": [{"date": "2026-06-10", "count": 50}]
    },
    {
      "short_code": "pQ7mN2j",
      "original_url": "https://google.com",
      "total_clicks": 80,
      "daily_visits": [{"date": "2026-06-10", "count": 30}]
    }
  ],
  "meta": {"period_days": 30, "links_compared": 2},
  "errors": null
}
```

### Data Collected Per Visit
| Field | Description |
|-------|-------------|
| `ip_address` | Anonymized IP (last octet removed for privacy) |
| `browser` | Browser name (Chrome, Firefox, Safari, etc.) |
| `os` | Operating system (Windows, macOS, iOS, etc.) |
| `device_type` | Mobile / Desktop / Tablet |
| `referrer` | Source URL of the visit |
| `country` | Country via GeoIP lookup |
| `city` | City via GeoIP lookup |
| `visited_at` | Precise timestamp |

### Non-blocking Collection
Analytics recording does **not** slow down the redirect response. The flow is:

```
User clicks link
      ↓
Immediate redirect (user sees no delay)
      ↓
Celery worker records visit data in the background:
  - Anonymizes IP
  - Parses User-Agent (browser, OS, device)
  - Stores in database
```

### GeoIP Lookup
Country and city are resolved via `ip-api.com` during async Celery processing — this never slows down the redirect.

> **Note:** In local Docker environments, all requests arrive via the Docker bridge network (`192.168.x.x`), so GeoIP lookup is skipped for private IPs. In production behind a reverse proxy (e.g. Nginx), the real client IP is passed via `X-Forwarded-For` and GeoIP works correctly.

### Time-Series Schema
The `visits` table uses composite indexes optimized for time-range queries:

```sql
INDEX ix_visits_link_visited_at  ON visits (link_id, visited_at)
INDEX ix_visits_visited_at       ON visits (visited_at)
```

This allows efficient queries like "clicks per day for the last 30 days" without full table scans.

### Celery Task Design
- `record_visit` task uses `max_retries=3` with exponential backoff
- If the task fails, it retries after 1s, 2s, 4s before giving up
- This ensures no visit data is lost due to temporary DB issues

---

## Webhook

Links support a webhook that fires once when a click threshold is reached.

### Setup — add to link creation request
```json
{
  "url": "https://example.com/long-url",
  "webhook_url": "https://your-site.com/webhook",
  "webhook_threshold": 1000
}
```

### Payload sent to your webhook URL
```json
{
  "event": "click_threshold_reached",
  "short_code": "aB3kR9x",
  "original_url": "https://example.com/long-url",
  "click_count": 1000,
  "threshold": 1000
}
```

**Guarantees:**
- Fires exactly once per link (`webhook_triggered` flag prevents duplicates)
- Retries up to 3 times on failure with exponential backoff
- Delivered asynchronously via Celery — does not affect redirect speed

---

## Dashboard

`GET /api/v1/dashboard/stats` returns an overview across all your links:

```json
{
  "total_links": 42,
  "total_clicks": 8750,
  "top_link": {
    "short_code": "aB3kR9x",
    "click_count": 3200
  },
  "by_device": [
    {"device": "Mobile", "count": 5100},
    {"device": "Desktop", "count": 3200},
    {"device": "Tablet", "count": 450}
  ]
}
```

---

## Testing

Run the test suite locally (outside Docker):

```bash
source venv/bin/activate
pytest tests/ -v
```

Tests use an in-memory SQLite database — no need to run Docker for tests.

### Test Results
```
tests/test_auth.py::test_register_success          PASSED
tests/test_auth.py::test_register_duplicate_email  PASSED
tests/test_auth.py::test_register_invalid_email    PASSED
tests/test_links.py::test_create_link_success      PASSED
tests/test_links.py::test_create_link_invalid_api_key  PASSED
tests/test_links.py::test_create_link_custom_alias PASSED
tests/test_links.py::test_create_duplicate_custom_alias PASSED
tests/test_links.py::test_get_links                PASSED
tests/test_links.py::test_delete_link              PASSED
tests/test_shortener.py::test_generate_random_code_length  PASSED
tests/test_shortener.py::test_generate_random_code_charset PASSED
tests/test_shortener.py::test_generate_unique_codes        PASSED
tests/test_shortener.py::test_pool_refill          PASSED
13 passed in ~2s
```

### Test Coverage
| File | What's tested |
|------|---------------|
| `test_auth.py` | Registration, duplicate email, invalid input |
| `test_shortener.py` | Code generation, uniqueness, pool refill |
| `test_links.py` | Create, list, delete, custom alias, auth validation |

---

*Last updated: June 2026*
