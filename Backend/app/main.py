import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from decimal import Decimal

from app.core.config import settings
from app.core.database import engine, SessionLocal, Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.settings import CompanySettings, TaxSettings
from app.models.product import Product, PriceHistory
from app.models.coupon import Coupon, CouponDiscountType
from app.api.v1.api import api_router

def init_db_and_seed():
    # Create tables
    Base.metadata.create_all(bind=engine)

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

        # 3. Seed Admin User
        admin = db.query(User).filter(User.email == "admin@livguard.com").first()
        if not admin:
            admin = User(
                email="admin@livguard.com",
                hashed_password=get_password_hash("Admin@123"),
                full_name="Livguard Central Admin",
                role=UserRole.ADMIN,
                mobile="9876543210",
                is_active=True
            )
            db.add(admin)
            db.flush()

        # 4. Seed Agent User
        agent = db.query(User).filter(User.email == "agent@livguard.com").first()
        if not agent:
            agent = User(
                email="agent@livguard.com",
                hashed_password=get_password_hash("Agent@123"),
                full_name="Vikram Sharma",
                role=UserRole.AGENT,
                mobile="9811223344",
                is_active=True
            )
            db.add(agent)
            db.flush()

        # 5. Seed Real Livguard Products (Lithium batteries, Inverters, Combos)
        products_data = [
            {
                "sku": "LG-LX-100AH",
                "name": "Livguard Lithium-X 100Ah / 12.8V Battery",
                "brand": "Livguard",
                "category": "Battery",
                "description": "Smart LiFePO4 Inverter Battery with 3X longer life, ultra-fast charging, and zero maintenance.",
                "price": Decimal("34999.00")
            },
            {
                "sku": "LG-LX-150AH",
                "name": "Livguard Lithium-X 150Ah / 12.8V Battery",
                "brand": "Livguard",
                "category": "Battery",
                "description": "High-capacity Lithium inverter battery engineered for heavy loads and high backup demand.",
                "price": Decimal("48500.00")
            },
            {
                "sku": "LG-XDT-1200",
                "name": "Livguard Lithium-XDT 1200 Smart Inverter",
                "brand": "Livguard",
                "category": "Inverter",
                "description": "Pure Sine Wave Smart Inverter with dynamic LCD display and multi-mode power optimization.",
                "price": Decimal("11200.00")
            },
            {
                "sku": "LG-XDT-1650",
                "name": "Livguard Lithium-XDT 1650 Heavy Duty Inverter",
                "brand": "Livguard",
                "category": "Inverter",
                "description": "Heavy duty commercial & home pure sine wave inverter with dual battery support.",
                "price": Decimal("14800.00")
            },
            {
                "sku": "LG-COMBO-PRO100",
                "name": "Livguard Smart Pro Combo 1200 + 100Ah Lithium-X",
                "brand": "Livguard",
                "category": "Combo",
                "description": "Complete Plug-and-play Backup Combo: XDT 1200 Inverter paired with 100Ah Lithium-X Battery.",
                "price": Decimal("44999.00")
            },
            {
                "sku": "LG-SLR-330W",
                "name": "Livguard Mono-PERC Solar Panel 330W",
                "brand": "Livguard",
                "category": "Solar",
                "description": "High-efficiency A-grade mono-PERC crystalline solar panel with 25-year performance warranty.",
                "price": Decimal("9200.00")
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
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db_and_seed()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}
