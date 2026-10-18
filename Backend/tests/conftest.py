import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.settings import CompanySettings, TaxSettings
from app.models.product import Product, PriceHistory
from app.models.coupon import Coupon, CouponDiscountType
from app.main import app

# In-memory SQLite for high-speed, isolated automated testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Seed core test records
    company = CompanySettings(
        company_name="Livguard Energy Technologies Pvt. Ltd.",
        tagline="More Power. Less Waiting.",
        logo_url="/assets/livguard_logo.png",
        address="Gurugram, Haryana",
        phone="1800-102-5551",
        email="support@livguard.com",
        website="www.livguard.com",
        terms_conditions="Standard 15 day validity.",
        quotation_validity_days=15,
        version=1
    )
    session.add(company)

    tax = TaxSettings(gst_rate=18.00, tax_name="GST (18%)", version=1)
    session.add(tax)

    admin = User(
        email="test_admin@livguard.com",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        mobile="9999999999",
        is_active=True
    )
    session.add(admin)
    session.flush()

    agent = User(
        email="test_agent@livguard.com",
        hashed_password=get_password_hash("AgentPass123"),
        full_name="Test Agent",
        role=UserRole.AGENT,
        mobile="8888888888",
        is_active=True
    )
    session.add(agent)
    session.flush()

    p1 = Product(
        sku="LG-TEST-100",
        name="Livguard 100Ah Lithium Battery",
        brand="Livguard",
        category="Battery",
        description="High durability battery",
        base_price=Decimal("30000.00"),
        is_active=True
    )
    session.add(p1)

    p2 = Product(
        sku="LG-TEST-INV",
        name="Livguard 1100VA Inverter",
        brand="Livguard",
        category="Inverter",
        description="Pure sine wave inverter",
        base_price=Decimal("10000.00"),
        is_active=True
    )
    session.add(p2)

    coupon = Coupon(
        code="SAVE10",
        discount_type=CouponDiscountType.PERCENTAGE,
        discount_value=Decimal("10.00"),
        max_discount=Decimal("5000.00"),
        min_subtotal=Decimal("10000.00"),
        usage_limit=10,
        is_active=True,
        created_by_id=admin.id
    )
    session.add(coupon)

    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)

from app.core.rate_limit import limiter

@pytest.fixture(scope="function")
def client(db_session):
    limiter.reset()
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()
