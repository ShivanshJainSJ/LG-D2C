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

        # 5. Seed Real Livguard Products (Combos, Inverters, Lead-Acid and Lithium Batteries)
        products_data = [
            {
                "sku": "LG-SET-1",
                "name": "Livguard Inverter + Battery Set – 1",
                "brand": "Livguard",
                "category": "Combo",
                "description": "• Livguard Inverter (1000 VA)\n• Livguard Invertuff Battery (150 Ah)\n• Advanced Sine Wave Technology\n• Fast Charging\n• Longer Backup & Life",
                "image_url": "/uploads/products/inverter_battery_combo.jpeg",
                "price": Decimal("22500.00")
            },
            {
                "sku": "LG-SET-2",
                "name": "Livguard Inverter + Battery Set – 2",
                "brand": "Livguard",
                "category": "Combo",
                "description": "• Livguard Inverter (1500 VA)\n• Livguard Invertuff Battery (200 Ah)\n• Advanced Sine Wave Technology\n• Fast Charging\n• Longer Backup & Life",
                "image_url": "/uploads/products/inverter_battery_combo.jpeg",
                "price": Decimal("28500.00")
            },
            {
                "sku": "LG-INV-1000",
                "name": "Livguard Pure Sine Wave Inverter 1000 VA",
                "brand": "Livguard",
                "category": "Inverter",
                "description": "• Pure Sine Wave Technology\n• Smart Dynamic Display\n• Fast Charging & Surge Protection\n• Silent Operation",
                "image_url": "/uploads/products/inverter.jpeg",
                "price": Decimal("8500.00")
            },
            {
                "sku": "LG-INV-1500",
                "name": "Livguard Heavy Duty Inverter 1500 VA",
                "brand": "Livguard",
                "category": "Inverter",
                "description": "• Pure Sine Wave Technology\n• Heavy Duty Load Support\n• Fast Charging & Low Maintenance",
                "image_url": "/uploads/products/inverter.jpeg",
                "price": Decimal("11500.00")
            },
            {
                "sku": "LG-BAT-150AH",
                "name": "Livguard Invertuff Tall Tubular Battery 150 Ah",
                "brand": "Livguard",
                "category": "Battery",
                "description": "• 150 Ah Deep Cycle Tall Tubular\n• Rugged Design & 3D Grid Alloy\n• Longer Backup & Extended Life",
                "image_url": "/uploads/products/lead_acid_battery.jpeg",
                "price": Decimal("14000.00")
            },
            {
                "sku": "LG-BAT-200AH",
                "name": "Livguard Invertuff Tall Tubular Battery 200 Ah",
                "brand": "Livguard",
                "category": "Battery",
                "description": "• 200 Ah Heavy Duty Tubular\n• High Backup Duration\n• Ultra Low Maintenance",
                "image_url": "/uploads/products/lead_acid_battery.jpeg",
                "price": Decimal("17000.00")
            },
            {
                "sku": "LG-LX-100AH",
                "name": "Livguard Smart Lithium Battery 100Ah / 12.8V",
                "brand": "Livguard",
                "category": "Battery",
                "description": "• LiFePO4 Smart Battery\n• 3X Longer Life Cycle\n• Superfast 2-Hour Charging\n• Zero Maintenance",
                "image_url": "/uploads/products/lithium_battery.jpeg",
                "price": Decimal("34999.00")
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
                # Update image_url and description if needed
                if not existing_p.image_url:
                    existing_p.image_url = p_data["image_url"]
                if not existing_p.description:
                    existing_p.description = p_data["description"]

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
