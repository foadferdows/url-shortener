# 🔗 URL Shortener

A production-ready URL shortening service with an analytics dashboard, built with **FastAPI**, **PostgreSQL**, **Redis**, and **Celery**.

---

## Features

- **URL Shortening** — Base62 short codes with custom alias support
- **Analytics** — Per-link stats: clicks by browser, device, country + multi-link comparison
- **Caching** — Redis Cache-Aside pattern with hot link detection
- **Background Processing** — Non-blocking analytics via Celery workers
- **Webhooks** — Fire an event when a click threshold is reached
- **Dashboard** — Aggregated stats across all your links
- **API Key Auth** — Simple and secure authentication

---

## Tech Stack

| Technology | Role |
|------------|------|
| **FastAPI** | Web framework + auto Swagger docs |
| **PostgreSQL** | Primary database |
| **Redis** | Cache + Celery message broker |
| **Celery** | Background task processing |
| **Docker** | Containerization |

---

## Quick Start

```bash
git clone <your-repo>
cd url-shortener

# Set up environment
cp .env.example .env
# Edit .env and fill in SECRET_KEY (see below)

# Run everything
docker-compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

### Generate a SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## API Usage

### 1. Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

```json
{
  "data": {
    "email": "you@example.com",
    "api_key": "sk_abc123...",
    "message": "Registration successful. Save your API key — it won't be shown again."
  },
  "meta": null,
  "errors": null
}
```

### 2. Create a Short Link

```bash
curl -X POST http://localhost:8000/api/v1/links \
  -H "x-api-key: sk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

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

### 3. Use the Short Link

```
GET http://localhost:8000/aB3kR9x
→ 302 redirect to original URL
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/auth/register` | No |

### Links
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/links` | Yes |
| GET | `/api/v1/links` | Yes |
| DELETE | `/api/v1/links/{short_code}` | Yes |

### Analytics & Dashboard
| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/api/v1/analytics/{short_code}` | Yes |
| GET | `/api/v1/analytics?days=30` | Yes |
| GET | `/api/v1/analytics/compare?codes=X,Y` | Yes |
| GET | `/api/v1/dashboard/stats` | Yes |

### Redirect & System
| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/{short_code}` | No |
| GET | `/health` | No |
| GET | `/docs` | No |

---

## Short Code Generation — Design Decision

**Chosen approach: Pre-generated Pool**

On startup, 1000 unique 7-character Base62 codes are pre-generated and stored in the database. When a user creates a link, a code is atomically claimed from the pool using `SELECT ... FOR UPDATE` to prevent race conditions. When the pool drops below 500 codes, it automatically refills.

**Why this approach over alternatives:**

| Approach | Latency | Race Condition Risk | Predictability |
|----------|---------|---------------------|----------------|
| Random with retry | Medium | Medium | Low |
| Counter-based | Low | Low | High (guessable) |
| **Pre-generated Pool** | **Low** | **None** | **Low (random)** |

**Trade-offs:** Requires an extra DB table and ~1000 pre-allocated rows at all times, but provides zero-latency code assignment with no race conditions.

**Capacity:** 62⁷ = ~3.5 trillion unique codes with 7-character Base62.

---

## Caching Strategy

**Pattern: Cache-Aside + Write-Through**

```
Redirect request
      ↓
Check Redis (cache_key = "link:{short_code}")
      ↓ hit                    ↓ miss
Serve from Redis         Fetch from DB
                               ↓
                         Store in Redis (TTL: 1hr)
                               ↓
                         Serve response
```

**TTL Policy:**
- Regular links: 1 hour
- Hot links (100+ clicks): 24 hours — extended automatically

**Cache Invalidation:** When a link is deleted, it is immediately removed from Redis.

**Click Counting:** Incremented in Redis first (fast), then flushed to DB via Celery (async).

---

## Analytics Pipeline

Visit data is collected **without slowing down the redirect**:

```
User clicks → Immediate 302 redirect
                    ↓
              Celery task (async):
              - Anonymize IP (remove last octet)
              - Parse User-Agent → browser, OS, device
              - Store Visit record in DB
```

**Data collected per visit:** timestamp, anonymized IP, browser, OS, device type, referrer, country, city.

> **GeoIP:** Country and city are resolved via `ip-api.com` asynchronously — never slows down redirect. Works with real public IPs in production.

---

## Webhook

When creating a link, you can configure a webhook to fire when a click threshold is reached:

```json
{
  "url": "https://example.com/long-url",
  "webhook_url": "https://your-site.com/webhook",
  "webhook_threshold": 1000
}
```

The webhook fires **exactly once** per link and is delivered asynchronously via Celery with up to 3 retries on failure.

---

## Rate Limiting

| User Type | Limit | Window |
|-----------|-------|--------|
| Unauthenticated (per IP) | 100 req/min | 60 seconds |
| Authenticated (per API Key) | 1000 req/min | 60 seconds |

Exceeding the limit returns `HTTP 429 Too Many Requests`.

---

## Link Features

Optional fields when creating a link:

| Field | Description |
|-------|-------------|
| `custom_alias` | Custom short code instead of auto-generated |
| `expires_at` | Link auto-expires at this datetime |
| `password` | Password gate — access via `?password=X` |
| `webhook_url` | URL to notify when click threshold is reached |
| `webhook_threshold` | Click count that triggers the webhook |

---

## Pagination

Link listings support cursor-based pagination:

```bash
GET /api/v1/links?limit=20&cursor=CURSOR
```

Response includes `meta.next_cursor` and `meta.has_more` for navigating pages.

---

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

13 tests — no Docker required (uses SQLite in-memory DB).

---

## Project Structure

```
url-shortener/
├── app/
│   ├── main.py              # Entry point
│   ├── database.py          # DB connection
│   ├── api/v1/              # Endpoints
│   │   ├── auth.py
│   │   ├── links.py
│   │   ├── redirect.py
│   │   ├── analytics.py
│   │   └── dashboard.py
│   ├── models/              # DB tables
│   ├── services/            # Business logic
│   ├── cache/               # Redis helpers
│   ├── schemas/             # Response envelope
│   └── workers/             # Celery tasks
├── tests/
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── requirements.txt
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | Random secret (generate with `secrets.token_hex(32)`) |
| `BASE_URL` | Public base URL of the service |
| `CELERY_BROKER_URL` | Celery broker (Redis) |
| `CELERY_RESULT_BACKEND` | Celery results (Redis) |
