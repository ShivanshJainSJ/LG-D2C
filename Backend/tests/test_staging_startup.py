import os
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.models.user import User, UserRole
from app.models.product import Product, PriceHistory
from app.models.coupon import Coupon
from app.models.settings import CompanySettings, TaxSettings
from app.main import init_db_and_seed, lifespan

def _create_isolated_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, Session

def test_staging_startup_without_initial_admin():
    """Verify staging startup succeeds safely without demo credentials or initial admin."""
    engine, Session = _create_isolated_db()
    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = None
        settings.INITIAL_ADMIN_PASSWORD = None

        # Must not raise UnboundLocalError or any exception
        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            # 1. No users should exist (zero demo credentials in staging)
            users = db.query(User).all()
            assert len(users) == 0
            assert db.query(User).filter(User.email == "admin@livguard.com").first() is None
            assert db.query(User).filter(User.email == "agent@livguard.com").first() is None

            # 2. Company & Tax settings should be initialized
            company = db.query(CompanySettings).first()
            assert company is not None
            assert company.company_name == "Livguard Energy Technologies Pvt. Ltd."
            tax = db.query(TaxSettings).first()
            assert tax is not None
            assert tax.gst_rate == Decimal("18.00")

            # 3. Products should be seeded cleanly
            products = db.query(Product).all()
            assert len(products) == 8
            for p in products:
                assert p.is_active is True
                assert p.base_price > 0

            # 4. PriceHistory should be skipped since no admin exists (no FK/null constraint violation)
            price_histories = db.query(PriceHistory).all()
            assert len(price_histories) == 0

            # 5. Coupon should be skipped since no admin exists to associate as creator
            coupon = db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first()
            assert coupon is None
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_startup_with_existing_admin_but_no_initial_admin_configured():
    """Verify when an active admin exists in DB but INITIAL_ADMIN_EMAIL is not configured,
    startup does NOT select that account for seed attribution, does not modify it, and
    skips records requiring an explicit administrator actor.
    """
    engine, Session = _create_isolated_db()
    Base.metadata.create_all(bind=engine)
    db = Session()
    pre_existing_admin = User(
        email="existing-admin@company.com",
        hashed_password="hashed_password_123",
        full_name="Existing Staging Admin",
        role=UserRole.ADMIN,
        mobile="9876543210",
        is_active=True
    )
    db.add(pre_existing_admin)
    db.commit()
    pre_admin_id = pre_existing_admin.id
    db.close()

    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = None
        settings.INITIAL_ADMIN_PASSWORD = None

        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            # 1. Existing admin is preserved without modification
            admin = db.query(User).filter(User.id == pre_admin_id).first()
            assert admin is not None
            assert admin.email == "existing-admin@company.com"
            assert admin.full_name == "Existing Staging Admin"
            assert admin.role == UserRole.ADMIN
            assert admin.is_active is True

            # No extra users created
            assert db.query(User).count() == 1

            # 2. Products are seeded cleanly
            products = db.query(Product).all()
            assert len(products) == 8

            # 3. Because INITIAL_ADMIN_EMAIL was not configured, the existing admin was NOT selected as an actor
            # PriceHistory should be skipped (0 records)
            assert db.query(PriceHistory).count() == 0

            # Coupon LIVGUARD10 should be skipped (not attributed to the unconfigured existing admin)
            assert db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first() is None
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_startup_with_initial_admin():
    """Verify staging startup with INITIAL_ADMIN bootstraps admin and seeds actor-dependent entities."""
    engine, Session = _create_isolated_db()
    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = "staging-lead@livguard.com"
        settings.INITIAL_ADMIN_PASSWORD = "StrongStagingPassword#2026"

        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            # 1. Staging initial admin created; demo accounts skipped
            admin = db.query(User).filter(User.email == "staging-lead@livguard.com").first()
            assert admin is not None
            assert admin.role == UserRole.ADMIN
            assert admin.is_active is True
            assert db.query(User).filter(User.email == "admin@livguard.com").first() is None
            assert db.query(User).filter(User.email == "agent@livguard.com").first() is None

            # 2. Products seeded with PriceHistory attributed to staging admin
            products = db.query(Product).all()
            assert len(products) == 8
            price_histories = db.query(PriceHistory).all()
            assert len(price_histories) == 8
            for ph in price_histories:
                assert ph.changed_by_id == admin.id

            # 3. Sample coupon seeded with created_by_id attributed to staging admin
            coupon = db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first()
            assert coupon is not None
            assert coupon.created_by_id == admin.id
            assert coupon.is_active is True
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_startup_repeated_runs_idempotent():
    """Verify repeated seeding calls are completely idempotent and do not duplicate records."""
    engine, Session = _create_isolated_db()
    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = "staging-admin@company.com"
        settings.INITIAL_ADMIN_PASSWORD = "StagingSecretPassword2026!"

        # First run
        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        # Second run on the exact same database
        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            assert db.query(User).count() == 1
            assert db.query(Product).count() == 8
            assert db.query(PriceHistory).count() == 8
            assert db.query(CompanySettings).count() == 1
            assert db.query(TaxSettings).count() == 1
            assert db.query(Coupon).count() == 1
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_subsequent_admin_provisioning():
    """Verify when an admin is configured after an initial headless run, coupon is created and catalog is preserved."""
    engine, Session = _create_isolated_db()
    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        # Step 1: Headless run in staging without admin
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = None
        settings.INITIAL_ADMIN_PASSWORD = None
        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        assert db.query(User).count() == 0
        assert db.query(Product).count() == 8
        assert db.query(Coupon).count() == 0
        db.close()

        # Step 2: Second run with initial admin configured
        settings.INITIAL_ADMIN_EMAIL = "admin.post@company.com"
        settings.INITIAL_ADMIN_PASSWORD = "PostProvisionPassword123!"
        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            admin = db.query(User).filter(User.email == "admin.post@company.com").first()
            assert admin is not None
            assert db.query(Product).count() == 8
            # Coupon LIVGUARD10 is now seeded and assigned to the new admin
            coupon = db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first()
            assert coupon is not None
            assert coupon.created_by_id == admin.id
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_startup_failure_propagates_in_lifespan(monkeypatch):
    """Ensure database initialization errors are never swallowed in staging or production."""
    import asyncio
    orig_env = settings.ENVIRONMENT

    def _failing_init():
        raise ConnectionError("Simulated Staging Database Connection Refused")

    async def _test():
        # Staging must raise
        settings.ENVIRONMENT = "staging"
        monkeypatch.setenv("TESTING", "0")
        monkeypatch.setattr("app.main.init_db_and_seed", _failing_init)

        with pytest.raises(ConnectionError, match="Simulated Staging Database Connection Refused"):
            async with lifespan(None):
                pass

        # Production must raise
        settings.ENVIRONMENT = "production"
        with pytest.raises(ConnectionError, match="Simulated Staging Database Connection Refused"):
            async with lifespan(None):
                pass

    try:
        asyncio.run(_test())
    finally:
        settings.ENVIRONMENT = orig_env


def test_staging_startup_rejects_inactive_initial_admin_account():
    """Verify that if INITIAL_ADMIN_EMAIL exists but is inactive, bootstrap refuses to treat it as valid admin."""
    engine, Session = _create_isolated_db()
    Base.metadata.create_all(bind=engine)
    db = Session()
    db.add(User(
        email="inactive-admin@company.com",
        hashed_password="somehashedpassword",
        full_name="Deactivated Admin",
        role=UserRole.ADMIN,
        is_active=False
    ))
    db.commit()
    db.close()

    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = "inactive-admin@company.com"
        settings.INITIAL_ADMIN_PASSWORD = "Password#12345"

        with pytest.raises(ValueError, match="is not an active administrator"):
            init_db_and_seed(db_engine=engine, db_session_factory=Session)
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_staging_startup_rejects_non_admin_role_initial_admin():
    """Verify that if INITIAL_ADMIN_EMAIL exists as a non-admin role (AGENT), bootstrap refuses to treat it as admin."""
    engine, Session = _create_isolated_db()
    Base.metadata.create_all(bind=engine)
    db = Session()
    db.add(User(
        email="sales-agent@company.com",
        hashed_password="somehashedpassword",
        full_name="Sales Agent",
        role=UserRole.AGENT,
        is_active=True
    ))
    db.commit()
    db.close()

    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "staging"
        settings.INITIAL_ADMIN_EMAIL = "sales-agent@company.com"
        settings.INITIAL_ADMIN_PASSWORD = "Password#12345"

        with pytest.raises(ValueError, match="is not an active administrator"):
            init_db_and_seed(db_engine=engine, db_session_factory=Session)
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd


def test_development_startup_preserves_demo_credentials():
    """Ensure development environment continues to seed demo credentials and actors."""
    engine, Session = _create_isolated_db()
    orig_env = settings.ENVIRONMENT
    orig_admin_email = settings.INITIAL_ADMIN_EMAIL
    orig_admin_pwd = settings.INITIAL_ADMIN_PASSWORD

    try:
        settings.ENVIRONMENT = "development"
        settings.INITIAL_ADMIN_EMAIL = None
        settings.INITIAL_ADMIN_PASSWORD = None

        init_db_and_seed(db_engine=engine, db_session_factory=Session)

        db = Session()
        try:
            admin = db.query(User).filter(User.email == "admin@livguard.com").first()
            assert admin is not None
            assert admin.role == UserRole.ADMIN

            agent = db.query(User).filter(User.email == "agent@livguard.com").first()
            assert agent is not None
            assert agent.role == UserRole.AGENT

            # Products have price history linked to dev admin
            price_histories = db.query(PriceHistory).all()
            assert len(price_histories) == 8
            for ph in price_histories:
                assert ph.changed_by_id == admin.id

            # Coupon is seeded and linked to dev admin
            coupon = db.query(Coupon).filter(Coupon.code == "LIVGUARD10").first()
            assert coupon is not None
            assert coupon.created_by_id == admin.id
        finally:
            db.close()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.INITIAL_ADMIN_EMAIL = orig_admin_email
        settings.INITIAL_ADMIN_PASSWORD = orig_admin_pwd
