# Livguard Quotation Management System

A production-grade D2C Quotation & Order Management Platform built for **Livguard Energy Technologies**.

---

## 🚀 Key Architectural Highlights

- **Backend**: Python FastAPI with SQLAlchemy 2.0, Pydantic v2, Alembic migrations, and JWT + Cookie-based RBAC authentication.
- **Frontend**: Next.js 15 (App Router), React 19, Tailwind CSS, Lucide icons.
- **Database**: Dual-engine design. Supports local zero-config SQLite (`livguard.db`) and hosted PostgreSQL (Neon, Supabase, AWS RDS).
- **Document Engine**: Headless Chromium (Playwright) generating print-ready selectable vector PDFs and high-resolution (2x DPI) PNGs reproducing Livguard's official quotation and order confirmation templates.
- **Transactional Numbering**: Safe sequence generator with database row-level locking for both quotation numbers (`LG/26/0001`) and confirmed order numbers (`ORD/26/0001`).
- **Controlled Revisions**: Immutable snapshot preservation for all issued quotation versions (`Revision 0`, `Revision 1`, `Revision 2`).
- **Payment & Order Separation**: Agents submit full payment reports with transaction reference numbers; Central Admin verifies payment before authorizing official Order Received documents.

---

## 🔐 Role-Based Access Control (RBAC)

The platform enforces strict role-based access control across all workflows:

- **Central Admin**: Full product catalog management, bulk CSV/XLSX product import with conflict resolution, price history auditing, statutory tax configuration, payment verification, and order confirmation.
- **Field Agent**: Customer identification by mobile number, SKU catalog exploration with automatic category image mapping, quotation drafting and issuance, immutable revision tracking, and payment reporting.

User accounts are authenticated securely via database-backed password hashing (bcrypt), signed JSON Web Tokens (JWT), and secure cookies.

---

## 🛠️ Running Locally

### 1. Backend Service

```bash
cd Backend
# Activate the virtual environment
.\.venv\Scripts\activate

# Run database migrations
alembic upgrade head

# Start FastAPI server (runs on http://127.0.0.1:8000)
uvicorn app.main:app --reload --port 8000
```

- API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend Web Application

```bash
cd Frontend
# Install dependencies (already completed)
npm install

# Start Next.js development server (runs on http://localhost:3000)
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) in your web browser.

---

## 🧪 Automated Testing

All 11 automated test suites have been executed and verified:

```bash
cd Backend
.\.venv\Scripts\pytest -v
```

### Verified Test Cases (46 Tests Passing):
1. `tests/test_auth.py`: Admin/Agent login, password verification, RBAC boundary enforcement.
2. `tests/test_category_images.py`: Category definitions and canonical 5-category asset mapping.
3. `tests/test_customers_and_quotation_history.py`: Phone normalization, returning customer identification, quotation reuse.
4. `tests/test_document_generation.py`: Playwright vector PDF and 2x DPI PNG rendering.
5. `tests/test_payments_and_orders.py`: Payment matching check, quotation freeze, admin verification, sequential order confirmation.
6. `tests/test_product_import.py`: XLSX/CSV template generation, duplicate SKU resolution, formula rejection.
7. `tests/test_production_readiness.py`: Liveness/readiness probes, security headers, rate limiting, quotation locking.
8. `tests/test_products_prices.py`: SKU uniqueness, price history auditing, product archiving.
9. `tests/test_quotations_and_revisions.py`: Sequential numbering, server-side recalculation, immutable revision snapshots.
10. `tests/test_security_remediation.py`: Production startup secret enforcement, secure cookies, logout cleanup, password complexity, session invalidation, private evidence isolation.

---

## 🌐 Production Deployment

### Database (Managed PostgreSQL / Neon)
1. Create a database instance on [Neon](https://neon.tech) or AWS RDS.
2. Set the connection string in `Backend/.env`:
   ```env
   DATABASE_URL="postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/livguard_db?sslmode=require"
   ```
3. Run `alembic upgrade head` to apply all schema migrations.

### Backend (Linux / Docker / Cloud Run)
Run with production ASGI workers:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend (Vercel)
Deploy the `Frontend` directory directly to Vercel and configure `NEXT_PUBLIC_API_URL` pointing to the hosted backend domain.
