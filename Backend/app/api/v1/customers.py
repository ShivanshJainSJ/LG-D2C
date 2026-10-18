from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_agent
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.customer import (
    CustomerLookupResponse,
    CustomerQuotationHistoryResponse,
    QuotationReuseResponse
)
from app.services.customer_service import CustomerService

router = APIRouter(tags=["Customers & Quotation History"])

@router.get("/customers/lookup", response_model=CustomerLookupResponse)
@limiter.limit("30/minute")
def lookup_customer(
    request: Request,
    mobile: str = Query(..., min_length=7, max_length=25, description="Customer raw mobile number"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Looks up a returning customer by mobile number, normalizing common formats.
    Returns customer details and recent quotation stats.
    """
    return CustomerService.lookup_by_mobile(
        db=db,
        raw_mobile=mobile,
        current_user=current_user,
        request=request
    )

@router.get("/agent/customers/lookup", response_model=CustomerLookupResponse)
@limiter.limit("30/minute")
def lookup_customer_agent_alias(
    request: Request,
    mobile: str = Query(..., min_length=7, max_length=25),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Agent alias for customer lookup."""
    return CustomerService.lookup_by_mobile(
        db=db,
        raw_mobile=mobile,
        current_user=current_user,
        request=request
    )

@router.get("/customers/{customer_id}/quotations", response_model=CustomerQuotationHistoryResponse)
def get_customer_quotations(
    customer_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves paginated quotation history for an identified customer.
    Enforces authorization and audits cross-agent access.
    """
    return CustomerService.get_customer_quotation_history(
        db=db,
        customer_id=customer_id,
        current_user=current_user,
        page=page,
        limit=limit,
        search=search,
        request=request
    )

@router.get("/agent/customers/{customer_id}/quotations", response_model=CustomerQuotationHistoryResponse)
def get_customer_quotations_agent_alias(
    customer_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Agent alias for customer quotation history."""
    return CustomerService.get_customer_quotation_history(
        db=db,
        customer_id=customer_id,
        current_user=current_user,
        page=page,
        limit=limit,
        search=search,
        request=request
    )

@router.post("/quotations/{quotation_id}/reuse", response_model=QuotationReuseResponse)
def reuse_quotation_root(
    quotation_id: str,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Creates a new draft quotation based on a historical quotation.
    Revalidates prices against active catalog and revalidates coupons & taxes.
    """
    return CustomerService.reuse_quotation(
        db=db,
        source_quotation_id=quotation_id,
        current_agent=current_agent,
        request=request
    )
