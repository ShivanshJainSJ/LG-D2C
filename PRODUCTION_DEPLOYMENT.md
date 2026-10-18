# Livguard Quotation Management System — Production Deployment & Operations Guide

## 1. System Architecture Overview

The Livguard Quotation Management System is a robust enterprise direct-to-consumer (D2C) and agent quotation workflow platform built with:

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0 ORM, Pydantic v2, SlowAPI rate limiting, Playwright headless PDF/PNG document generation engine.
- **Frontend**: Next.js 15 (React 19), Tailwind CSS, Lucide icons, authenticated API client.
- **Database**: PostgreSQL (Neon Serverless PostgreSQL with SSL `sslmode=require` or self-hosted PostgreSQL 15+). SQLite is natively supported for rapid zero-dependency local testing.
- **Storage**: Local filesystem volume or S3-compatible object storage mounted at `/uploads`.

---

## 2. Environment Configuration

### Backend (`Backend/.env`)

```ini
PROJECT_NAME="Livguard Quotation Management System"
VERSION="1.0.0"
API_V1_STR="/api/v1"
ENVIRONMENT="production"

# Generate a 64+ character random secret: openssl rand -hex 32
SECRET_KEY="<YOUR_PRODUCTION_SECRET_KEY>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Neon PostgreSQL Connection (Direct or PgBouncer Pooled)
DATABASE_URL="postgresql://neondb_owner:<PASSWORD>@<HOST>/neondb?sslmode=require"

# CORS Allowed Origins (JSON array format)
BACKEND_CORS_ORIGINS=["https://quotations.livguard.com", "https://admin.livguard.com"]

# Upload Directory Path
UPLOAD_DIR="./uploads"
```

### Frontend (`Frontend/.env.production` or platform env)

```ini
NEXT_PUBLIC_API_URL="https://api.quotations.livguard.com"
```

---

## 3. Database & Concurrency Hardening

### Connection Pooling & Dialect Handling
`app/core/database.py` dynamically identifies the database engine:
- When connecting to **PostgreSQL / Neon**, it automatically applies production pool parameters:
  - `pool_size`: 10
  - `max_overflow`: 20
  - `pool_recycle`: 300 seconds
  - `pool_timeout`: 30 seconds
  - `pool_pre_ping`: True (detects and discards stale / disconnected sockets)
- Automatically normalizes legacy `postgres://` connection URLs to `postgresql://`.

### Atomic Quotation Numbering (`LG/{YY}/{SEQ}`)
- Sequence allocation uses database row-level locking (`with_for_update()`) on table `number_sequences`.
- Unique constraint `uq_number_sequence_type_year` strictly prevents duplicate quotation numbers across concurrent worker processes.
- Formats dynamically based on calendar year: `LG/26/0001` for year 2026.

### Composite Database Indexes
The following performance indexes are enforced:
- **Products**: `(sku)`, `(name)`, `(category)`, `(is_active)`, `(category, is_active)`
- **Quotations**: `(quotation_number)`, `(agent_id, status)`, `(status, created_at)`, `(customer_mobile)`
- **Audit Logs**: `(actor_id)`, `(action)`, `(entity_type, entity_id)`, `(created_at)`
- **Customers**: `(mobile)`, `(name)`, `(created_at)`

---

## 4. Security & Hardening Controls

### Rate Limiting (SlowAPI)
- **Login Endpoint** (`POST /api/v1/auth/login`): Enforced at `10 requests/minute` per IP address.
- **Password Reset** (`POST /api/v1/auth/change-password`): Enforced at `5 requests/minute`.
- Exceeding limits returns standard HTTP `429 Too Many Requests`.

### HTTP Security Headers
Every HTTP response automatically includes:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enabled when `ENVIRONMENT=production`)
- `X-Request-ID`: Propagates tracing ID across request-response cycle.

### Authentication & Cookies
- In production (`ENVIRONMENT=production`), browser cookies are issued with `Secure=True`, `HttpOnly=True`, and `SameSite=Lax`.

---

## 5. Health & Observability Probes

The backend exposes 3 dedicated health and probe endpoints:

1. **`GET /health`**: Fast backward-compatible ping (`200 OK {"status": "ok"}`).
2. **`GET /healthz`**: Kubernetes / Docker container liveness probe.
3. **`GET /readyz`**: Deep readiness probe verifying:
   - Database live connectivity via `SELECT 1` ping.
   - Upload directory existence and write permissions.
   - Returns `200 OK {"status": "ready"}` or `503 Service Unavailable` with details.

---

## 6. Docker Deployment

### Single-Command Start via Docker Compose

```bash
docker compose up -d --build
```

### Inspecting Container Health

```bash
docker compose ps
docker compose logs -f backend
```

---

## 7. Automated Testing & Verification

Run the complete test suite:

```bash
# In Backend/
pytest -v

# In Frontend/
npm run build
```
