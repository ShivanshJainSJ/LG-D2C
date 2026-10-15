from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.settings import CompanySettings, TaxSettings
from app.schemas.settings import CompanySettingsUpdate, CompanySettingsResponse, TaxSettingsUpdate, TaxSettingsResponse

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])

DEFAULT_TERMS = """1. Price Validity: This quotation is valid for 15 days from the date of issue.
2. Payment: 100% advance payment required upon order confirmation.
3. Delivery: Goods will be dispatched within 3-5 business days upon verified payment.
4. Warranty: Standard Livguard manufacturer warranty applies as per product warranty card.
5. Installation: Complimentary standard installation by certified Livguard technicians.
6. Taxes: Statutory GST applicable as per Government of India regulations."""

def get_or_create_company_settings(db: Session) -> CompanySettings:
    settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    if not settings:
        settings = CompanySettings(
            company_name="Livguard Energy Technologies Pvt. Ltd.",
            tagline="More Power. Less Waiting.",
            logo_url="/assets/livguard_logo.png",
            address="Plot No. 221, Udyog Vihar, Phase 1, Sector 20, Gurugram, Haryana 122016",
            phone="1800-102-5551",
            email="support@livguard.com",
            website="www.livguard.com",
            terms_conditions=DEFAULT_TERMS,
            quotation_validity_days=15,
            version=1
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

def get_or_create_tax_settings(db: Session) -> TaxSettings:
    tax = db.query(TaxSettings).order_by(TaxSettings.version.desc()).first()
    if not tax:
        tax = TaxSettings(
            gst_rate=18.00,
            tax_name="GST (18%)",
            version=1
        )
        db.add(tax)
        db.commit()
        db.refresh(tax)
    return tax

@router.get("/company", response_model=CompanySettingsResponse)
def get_company_settings(current_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return get_or_create_company_settings(db)

@router.put("/company", response_model=CompanySettingsResponse)
def update_company_settings(
    settings_in: CompanySettingsUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    current = get_or_create_company_settings(db)
    
    # Version increment
    if settings_in.company_name is not None: current.company_name = settings_in.company_name
    if settings_in.tagline is not None: current.tagline = settings_in.tagline
    if settings_in.logo_url is not None: current.logo_url = settings_in.logo_url
    if settings_in.address is not None: current.address = settings_in.address
    if settings_in.phone is not None: current.phone = settings_in.phone
    if settings_in.email is not None: current.email = settings_in.email
    if settings_in.website is not None: current.website = settings_in.website
    if settings_in.terms_conditions is not None: current.terms_conditions = settings_in.terms_conditions
    if settings_in.quotation_validity_days is not None: current.quotation_validity_days = settings_in.quotation_validity_days
    if settings_in.numbering_policy is not None: current.numbering_policy = settings_in.numbering_policy
    if settings_in.year_boundary_month is not None: current.year_boundary_month = settings_in.year_boundary_month
    if settings_in.currency_symbol is not None: current.currency_symbol = settings_in.currency_symbol

    current.version += 1
    db.commit()
    db.refresh(current)

    log_audit_event(db, current_admin, "UPDATE_COMPANY_SETTINGS", "CompanySettings", current.id, {"version": current.version}, request)
    return current

@router.get("/tax", response_model=TaxSettingsResponse)
def get_tax_settings(current_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return get_or_create_tax_settings(db)

@router.put("/tax", response_model=TaxSettingsResponse)
def update_tax_settings(
    tax_in: TaxSettingsUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    current = get_or_create_tax_settings(db)
    
    # Versioning: new settings affect future quotations without changing past ones
    current.gst_rate = tax_in.gst_rate
    current.pricing_policy = tax_in.pricing_policy
    current.tax_name = tax_in.tax_name
    current.is_active = tax_in.is_active
    current.version += 1

    db.commit()
    db.refresh(current)

    log_audit_event(db, current_admin, "UPDATE_TAX_SETTINGS", "TaxSettings", current.id, {"rate": str(current.gst_rate), "policy": current.pricing_policy.value}, request)
    return current
