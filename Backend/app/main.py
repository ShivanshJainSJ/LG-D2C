import os
import uuid
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, SessionLocal, Base
from app.core.security import get_password_hash
from app.core.rate_limit import limiter
from app.models.user import User, UserRole
from app.models.settings import CompanySettings, TaxSettings
from app.models.coupon import Coupon, CouponDiscountType
from app.models.product import Product, PriceHistory
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.core.phone import normalize_phone_number
from app.api.v1.api import api_router
from app.core.product_categories import (
    ProductCategory,
    normalize_category_key,
    get_category_image_url,
    CATEGORY_IMAGE_ASSETS
)

def init_db_and_seed():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Ensure schema migrations for newly added columns if table pre-existed
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT normalized_mobile FROM customers LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE customers ADD COLUMN normalized_mobile VARCHAR(30)"))
                conn.execute(text("ALTER TABLE customers ADD COLUMN mobile_display VARCHAR(50)"))
                conn.execute(text("ALTER TABLE customers ADD COLUMN created_by_agent_id VARCHAR(36)"))
                conn.execute(text("ALTER TABLE customers ADD COLUMN last_contacted_at DATETIME"))
                conn.execute(text("ALTER TABLE customers ADD COLUMN updated_at DATETIME"))
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute(text("SELECT customer_id FROM quotations LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE quotations ADD COLUMN customer_id VARCHAR(36)"))
                conn.execute(text("ALTER TABLE quotations ADD COLUMN source_quotation_id VARCHAR(36)"))
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute(text("SELECT password_changed_at FROM users LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME"))
                conn.commit()
            except Exception:
                pass

    db = SessionLocal()
    try:
        # 1. Seed Company Settings if not present
        comp = db.query(CompanySettings).first()
        if not comp:
            terms = """1. Price Validity: This quotation is strictly valid for 15 days from the date of issue.
2. Payment Terms: 100% advance payment required upon order confirmation via NEFT/RTGS, UPI, or NetBanking.
3. Delivery: Goods will be dispatched within 3-5 business days upon payment verification.
4. Warranty: Standard Livguard manufacturer warranty applies as per product specifications card.
5. Installation: Complimentary standard installation by certified Livguard authorized service technicians.
6. Statutory Taxes: GST is charged as per Government of India statutory rates."""

            comp = CompanySettings(
                company_name="Livguard Energy Technologies Pvt. Ltd.",
                tagline="More Power. Less Waiting.",
                logo_url="/assets/livguard_logo.png",
                address="Plot No. 221, Udyog Vihar, Phase 1, Sector 20, Gurugram, Haryana 122016",
                phone="1800-102-5551",
                email="support@livguard.com",
                website="www.livguard.com",
                terms_conditions=terms,
                quotation_validity_days=15,
                version=1
            )
            db.add(comp)

        # 2. Seed Tax Settings if not present
        tax = db.query(TaxSettings).first()
        if not tax:
            tax = TaxSettings(
                gst_rate=18.00,
                tax_name="GST (18%)",
                version=1
            )
            db.add(tax)

        # 3. Seed Users based on Environment
        if settings.ENVIRONMENT in ("development", "test"):
            # Seed Dev/Test Admin User if not already present
            admin = db.query(User).filter(User.email == "admin@livguard.com").first()
            if not admin:
                init_admin_pwd = os.getenv("INITIAL_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD", "Admin@123")
                admin = User(
                    email="admin@livguard.com",
                    hashed_password=get_password_hash(init_admin_pwd),
                    full_name="Livguard Central Admin",
                    role=UserRole.ADMIN,
                    mobile="9876543210",
                    is_active=True
                )
                db.add(admin)
                db.flush()

            # Seed Dev/Test Agent User if not already present
            agent = db.query(User).filter(User.email == "agent@livguard.com").first()
            if not agent:
                init_agent_pwd = os.getenv("INITIAL_AGENT_PASSWORD") or os.getenv("AGENT_PASSWORD", "Agent@123")
                agent = User(
                    email="agent@livguard.com",
                    hashed_password=get_password_hash(init_agent_pwd),
                    full_name="Vikram Sharma",
                    role=UserRole.AGENT,
                    mobile="9811223344",
                    is_active=True
                )
                db.add(agent)
                db.flush()
        else:
            # Production: NEVER seed publicly known demo credentials
            logging.info("Production mode: skipping default demo credentials seeding.")
            if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
                prod_admin = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL.strip().lower()).first()
                if not prod_admin:
                    prod_admin = User(
                        email=settings.INITIAL_ADMIN_EMAIL.strip().lower(),
                        hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                        full_name="Production Administrator",
                        role=UserRole.ADMIN,
                        is_active=True
                    )
                    db.add(prod_admin)
                    db.flush()
                    logging.info("Production initial admin account bootstrapped successfully.")

        # 5. Seed Real Livguard Products across all 5 canonical categories
        products_data = [
            {
                "sku": "LG-SET-1",
                "name": "Livguard Inverter + Battery Set – 1",
                "brand": "Livguard",
                "category": ProductCategory.LEAD_ACID_INVERTER_COMBO.value,
                "description": "• Livguard Inverter (1000 VA)\n• Livguard Invertuff Battery (150 Ah)\n• Advanced Sine Wave Technology\n• Fast Charging\n• Longer Backup & Life",
                "image_url": "/uploads/products/leadinvertercombo.png",
                "price": Decimal("22500.00")
            },
            {
                "sku": "LG-SET-2",
                "name": "Livguard Inverter + Battery Set – 2",
                "brand": "Livguard",
                "category": ProductCategory.LEAD_ACID_INVERTER_COMBO.value,
                "description": "• Livguard Inverter (1500 VA)\n• Livguard Invertuff Battery (200 Ah)\n• Advanced Sine Wave Technology\n• Fast Charging\n• Longer Backup & Life",
                "image_url": "/uploads/products/leadinvertercombo.png",
                "price": Decimal("28500.00")
            },
            {
                "sku": "LG-INV-1000",
                "name": "Livguard Pure Sine Wave Inverter 1000 VA",
                "brand": "Livguard",
                "category": ProductCategory.INVERTER.value,
                "description": "• Pure Sine Wave Technology\n• Smart Dynamic Display\n• Fast Charging & Surge Protection\n• Silent Operation",
                "image_url": "/uploads/products/inverter.png",
                "price": Decimal("8500.00")
            },
            {
                "sku": "LG-INV-1500",
                "name": "Livguard Heavy Duty Inverter 1500 VA",
                "brand": "Livguard",
                "category": ProductCategory.INVERTER.value,
                "description": "• Pure Sine Wave Technology\n• Heavy Duty Load Support\n• Fast Charging & Low Maintenance",
                "image_url": "/uploads/products/inverter.png",
                "price": Decimal("11500.00")
            },
            {
                "sku": "LG-BAT-150AH",
                "name": "Livguard Invertuff Tall Tubular Battery 150 Ah",
                "brand": "Livguard",
                "category": ProductCategory.LEAD_ACID_BATTERY.value,
                "description": "• 150 Ah Deep Cycle Tall Tubular\n• Rugged Design & 3D Grid Alloy\n• Longer Backup & Extended Life",
                "image_url": "/uploads/products/LeadAcidBattery.jpeg",
                "price": Decimal("14000.00")
            },
            {
                "sku": "LG-BAT-200AH",
                "name": "Livguard Invertuff Tall Tubular Battery 200 Ah",
                "brand": "Livguard",
                "category": ProductCategory.LEAD_ACID_BATTERY.value,
                "description": "• 200 Ah Heavy Duty Tubular\n• High Backup Duration\n• Ultra Low Maintenance",
                "image_url": "/uploads/products/LeadAcidBattery.jpeg",
                "price": Decimal("17000.00")
            },
            {
                "sku": "LG-LX-100AH",
                "name": "Livguard Smart Lithium Battery 100Ah / 12.8V",
                "brand": "Livguard",
                "category": ProductCategory.LITHIUM_BATTERY.value,
                "description": "• LiFePO4 Smart Battery\n• 3X Longer Life Cycle\n• Superfast 2-Hour Charging\n• Zero Maintenance",
                "image_url": "/uploads/products/Lithium Battery.jpeg",
                "price": Decimal("34999.00")
            },
            {
                "sku": "LG-COMBO-PRO100",
                "name": "Livguard Smart Pro Combo 1200 + 100Ah Lithium-X",
                "brand": "Livguard",
                "category": ProductCategory.LITHIUM_INVERTER_COMBO.value,
                "description": "• 1200VA Sine Wave Smart Inverter\n• 100Ah Lithium-X Iron Phosphate Battery\n• Integrated Smart BMS & Fast Charging\n• 5 Years Comprehensive Warranty",
                "image_url": "/uploads/products/Lithiuminvertercombo.jpeg",
                "price": Decimal("48000.00")
            }
        ]

        for p_data in products_data:
            existing_p = db.query(Product).filter(Product.sku == p_data["sku"]).first()
            if not existing_p:
                p = Product(
                    sku=p_data["sku"],
                    name=p_data["name"],
                    brand=p_data["brand"],
                    category=p_data["category"],
                    description=p_data["description"],
                    image_url=p_data["image_url"],
                    base_price=p_data["price"],
                    is_active=True
                )
                db.add(p)
                db.flush()
                db.add(PriceHistory(
                    product_id=p.id,
                    old_price=Decimal("0.00"),
                    new_price=p.base_price,
                    changed_by_id=admin.id,
                    reason="Initial catalog seeding"
                ))
            else:
                existing_p.category = p_data["category"]
                existing_p.image_url = p_data["image_url"]
                if not existing_p.description:
                    existing_p.description = p_data["description"]

        # Migrate all existing products in DB to canonical categories and default category images
        all_prods = db.query(Product).all()
        for prod in all_prods:
            norm = normalize_category_key(prod.category)
            if not norm:
                s_lower = (prod.sku + " " + prod.name).lower()
                if "lithium" in s_lower and ("combo" in s_lower or "xdt" in s_lower and "combo" in s_lower):
                    norm = ProductCategory.LITHIUM_INVERTER_COMBO.value
                elif "set" in s_lower or "combo" in s_lower:
                    norm = ProductCategory.LEAD_ACID_INVERTER_COMBO.value
                elif "lithium" in s_lower or "lx" in s_lower:
                    norm = ProductCategory.LITHIUM_BATTERY.value
                elif "bat" in s_lower or "tubular" in s_lower:
                    norm = ProductCategory.LEAD_ACID_BATTERY.value
                else:
                    norm = ProductCategory.INVERTER.value
            prod.category = norm
            if not prod.image_url or not str(prod.image_url).strip() or "inverter_battery_combo" in prod.image_url or "inverter.jpeg" in prod.image_url:
                prod.image_url = get_category_image_url(prod.category)
        db.commit()

        # 6. Seed Sample Active Coupon
        coupon = db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first()
        if not coupon:
            coupon = Coupon(
                code="LIVGUARD10",
                discount_type=CouponDiscountType.PERCENTAGE,
                discount_value=Decimal("10.00"),
                max_discount=Decimal("5000.00"),
                min_subtotal=Decimal("20000.00"),
                usage_limit=100,
                per_agent_limit=20,
                is_active=True,
                created_by_id=admin.id
            )
            db.add(coupon)

        db.commit()

        # 7. Reconcile customers & backfill customer_id on quotations
        all_customers = db.query(Customer).all()
        seen_normalized = {}
        for c in all_customers:
            raw = c.mobile or c.normalized_mobile or "9876543210"
            try:
                norm, disp = normalize_phone_number(raw)
            except Exception:
                norm = f"+91{str(raw).strip()[-10:]}"
                disp = norm

            if norm not in seen_normalized:
                c.normalized_mobile = norm
                c.mobile_display = disp
                seen_normalized[norm] = c
            else:
                # Merge duplicate customer record
                canonical = seen_normalized[norm]
                for q in c.quotations:
                    q.customer_id = canonical.id
                db.delete(c)
        db.commit()

        # Link any quotations missing customer_id
        unlinked_quotations = db.query(Quotation).filter(Quotation.customer_id.is_(None)).all()
        for q in unlinked_quotations:
            try:
                norm, disp = normalize_phone_number(q.customer_mobile)
            except Exception:
                norm = f"+91{str(q.customer_mobile).strip()[-10:]}"
                disp = norm

            cust = db.query(Customer).filter(Customer.normalized_mobile == norm).first()
            if not cust:
                cust = Customer(
                    name=q.customer_name,
                    normalized_mobile=norm,
                    mobile_display=disp,
                    mobile=q.customer_mobile,
                    email=q.customer_email,
                    address=q.customer_address,
                    created_by_agent_id=q.agent_id,
                    last_contacted_at=q.created_at
                )
                db.add(cust)
                db.flush()
            q.customer_id = cust.id
        db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: bypass disk DB init during automated unit/integration testing
    if os.getenv("TESTING") == "1":
        yield
        return

    try:
        init_db_and_seed()
    except Exception as e:
        logging.exception(f"Database initialization error on startup: {e}")
        if settings.ENVIRONMENT == "production":
            raise e
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Attach rate limiter to app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request Correlation ID & Security Headers Middleware
@app.middleware("http")
async def security_and_correlation_middleware(request: Request, call_next):
    # Enforce HTTPS redirect in production when request is forwarded over plain HTTP
    if settings.ENVIRONMENT == "production":
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto == "http":
            from fastapi.responses import RedirectResponse
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=status.HTTP_301_MOVED_PERMANENTLY)

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    try:
        response = await call_next(request)
    except Exception as exc:
        if settings.ENVIRONMENT == "production":
            logging.exception(f"Unhandled error for request {request_id}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal server error occurred.",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
        raise exc

    # Enforce standard production security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Static file serving: only public product catalog images and brand assets are publicly accessible
public_products_dir = os.path.join(settings.UPLOAD_DIR, "products")
public_assets_dir = os.path.join(settings.UPLOAD_DIR, "assets")
os.makedirs(public_products_dir, exist_ok=True)
os.makedirs(public_assets_dir, exist_ok=True)
app.mount("/uploads/products", StaticFiles(directory=public_products_dir), name="uploads_products")
app.mount("/uploads/assets", StaticFiles(directory=public_assets_dir), name="uploads_assets")

# Mount API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health & Observability Endpoints
@app.get("/health", tags=["Health"])
def health_check():
    """Standard health check endpoint for backwards compatibility."""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

@app.get("/healthz", tags=["Health"])
def liveness_probe():
    """Liveness probe: returns 200 OK if service process is running."""
    return {"status": "alive", "timestamp": str(uuid.uuid1())}

@app.get("/readyz", tags=["Health"])
def readiness_probe():
    """Readiness probe: verifies database connectivity and file storage accessibility."""
    checks = {
        "database": "unknown",
        "storage": "unknown"
    }

    # 1. Database check
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        logging.error(f"Readiness probe database connection failure: {type(e).__name__} - {e}")
        checks["database"] = "unhealthy: connection failed"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks}
        )

    # 2. File storage check
    try:
        if os.path.exists(settings.UPLOAD_DIR) and os.access(settings.UPLOAD_DIR, os.W_OK):
            checks["storage"] = "healthy"
        else:
            checks["storage"] = "unhealthy: upload directory is not writable"
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "checks": checks}
            )
    except Exception as e:
        logging.error(f"Readiness probe storage check failure: {type(e).__name__} - {e}")
        checks["storage"] = "unhealthy: storage inaccessible"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks}
        )

    return {
        "status": "ready",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks
    }
