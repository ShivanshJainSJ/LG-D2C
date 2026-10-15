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

## 🔐 Default Demo Credentials

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Central Admin** | `admin@livguard.com` | `Admin@123` | Full CRUD, Price History, GST Settings, Payment Review, Order Confirmation |
| **Field Agent** | `agent@livguard.com` | `Agent@123` | SKU Lookup, Draft & Issue Quotations, Controlled Revisions, Report Payments |

*Quick login buttons are available on the `/login` page.*

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

### Verified Test Cases:
1. `tests/test_auth.py`: Admin login, agent login, invalid password rejection, RBAC boundary enforcement.
2. `tests/test_products_prices.py`: SKU uniqueness constraint, price adjustment audit log, product archive preservation.
3. `tests/test_quotations_and_revisions.py`: Sequential numbering (`LG/26/0001`), server-side price recalculation, immutable revision snapshots.
4. `tests/test_payments_and_orders.py`: Full payment matching check, quotation freeze on report, admin verification, sequential order confirmation (`ORD/26/0001`).
5. `tests/test_document_generation.py`: Playwright PDF and high-res PNG rendering using Livguard branded template.

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
