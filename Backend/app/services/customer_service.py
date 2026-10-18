from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Request
from decimal import Decimal

from app.core.phone import normalize_phone_number
from app.core.dependencies import log_audit_event
from app.models.customer import Customer
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.product import Product
from app.models.coupon import Coupon
from app.models.settings import CompanySettings, TaxSettings
from app.models.user import User, UserRole
from app.services.pricing_service import PricingService

class CustomerService:
    @staticmethod
    def get_or_create_customer(
        db: Session,
        name: str,
        raw_mobile: str,
        email: Optional[str] = None,
        address: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Customer:
        """
        Idempotently normalizes and finds or creates a customer by mobile number.
        Handles race conditions gracefully.
        """
        try:
            norm_mobile, disp_mobile = normalize_phone_number(raw_mobile)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mobile number: {str(e)}"
            )

        customer = db.query(Customer).filter(Customer.normalized_mobile == norm_mobile).first()
        now = datetime.now(timezone.utc)

        if customer:
            # Update customer details if provided
            if name and str(name).strip():
                customer.name = str(name).strip()
            if email and str(email).strip():
                customer.email = str(email).strip()
            if address and str(address).strip():
                customer.address = str(address).strip()
            customer.mobile_display = disp_mobile
            customer.last_contacted_at = now
            db.commit()
            return customer

        # Create new customer record
        new_customer = Customer(
            name=str(name).strip(),
            normalized_mobile=norm_mobile,
            mobile_display=disp_mobile,
            mobile=raw_mobile,
            email=str(email).strip() if email else None,
            address=str(address).strip() if address else None,
            created_by_agent_id=agent_id,
            last_contacted_at=now
        )
        try:
            db.add(new_customer)
            db.commit()
            db.refresh(new_customer)
            return new_customer
        except IntegrityError:
            db.rollback()
            # Concurrently created by another transaction
            existing = db.query(Customer).filter(Customer.normalized_mobile == norm_mobile).first()
            if existing:
                return existing
            raise

    @staticmethod
    def lookup_by_mobile(
        db: Session,
        raw_mobile: str,
        current_user: User,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Searches for a customer by raw mobile number and returns identification + quotation history summary.
        """
        try:
            norm_mobile, disp_mobile = normalize_phone_number(raw_mobile)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        customer = db.query(Customer).filter(Customer.normalized_mobile == norm_mobile).first()
        if not customer:
            return {
                "found": False,
                "normalized_mobile": norm_mobile,
                "mobile_display": disp_mobile,
                "customer": None,
                "stats": None
            }

        # Query all linked quotations
        quotes = db.query(Quotation).filter(
            (Quotation.customer_id == customer.id) | (Quotation.customer_mobile == norm_mobile) | (Quotation.customer_mobile == customer.mobile)
        ).order_by(Quotation.created_at.desc()).all()

        total_quotes = len(quotes)
        latest_quote = quotes[0] if quotes else None
        latest_rev = latest_quote.revisions[0] if (latest_quote and latest_quote.revisions) else None

        is_same_agent = (customer.created_by_agent_id == current_user.id)
        
        # Audit returning customer lookup when agent accesses customer record
        if request and not is_same_agent and current_user.role == UserRole.AGENT:
            log_audit_event(
                db, current_user, "VIEW_RETURNING_CUSTOMER_LOOKUP", "Customer", customer.id,
                {"normalized_mobile": norm_mobile, "created_by_agent_id": customer.created_by_agent_id},
                request
            )

        agent_creator = db.query(User).filter(User.id == customer.created_by_agent_id).first() if customer.created_by_agent_id else None

        return {
            "found": True,
            "normalized_mobile": norm_mobile,
            "mobile_display": customer.mobile_display or disp_mobile,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "normalized_mobile": customer.normalized_mobile,
                "mobile_display": customer.mobile_display or disp_mobile,
                "email": customer.email,
                "address": customer.address,
                "created_at": customer.created_at,
                "created_by_agent_id": customer.created_by_agent_id,
                "created_by_agent_name": agent_creator.full_name if agent_creator else None
            },
            "stats": {
                "total_quotations": total_quotes,
                "latest_quotation_number": latest_quote.quotation_number if latest_quote else None,
                "latest_quotation_date": latest_quote.created_at if latest_quote else None,
                "latest_quotation_status": latest_quote.status.value if latest_quote else None,
                "latest_quotation_grand_total": float(latest_rev.grand_total) if latest_rev else None,
                "created_by_same_agent": is_same_agent
            }
        }

    @staticmethod
    def get_customer_quotation_history(
        db: Session,
        customer_id: str,
        current_user: User,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Retrieves paginated quotation history for an identified customer with full authorization checks.
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Audit access to returning customer history
        if request and customer.created_by_agent_id != current_user.id and current_user.role == UserRole.AGENT:
            log_audit_event(
                db, current_user, "VIEW_RETURNING_CUSTOMER_QUOTATIONS", "Customer", customer.id,
                {"customer_name": customer.name, "created_by_agent_id": customer.created_by_agent_id},
                request
            )

        query = db.query(Quotation).filter(
            (Quotation.customer_id == customer.id) | (Quotation.customer_mobile == customer.normalized_mobile) | (Quotation.customer_mobile == customer.mobile)
        )

        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(Quotation.quotation_number.ilike(s))

        total = query.count()
        offset = (page - 1) * limit
        quotations = query.order_by(Quotation.created_at.desc()).offset(offset).limit(limit).all()

        company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
        validity_days = company_settings.quotation_validity_days if company_settings else 15

        items_res = []
        for q in quotations:
            rev = q.revisions[0] if q.revisions else None
            valid_until = q.created_at + timedelta(days=validity_days) if q.created_at else None

            # Collect items with current catalog pricing & active status
            product_items = []
            if rev:
                for item in rev.items:
                    prod = db.query(Product).filter(Product.sku == item.sku).first()
                    product_items.append({
                        "product_id": prod.id if prod else item.product_id,
                        "sku": item.sku,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "total_price": float(item.total_price),
                        "current_catalog_price": float(prod.base_price) if prod else None,
                        "is_active": prod.is_active if prod else False
                    })

            agent_user = q.agent or db.query(User).filter(User.id == q.agent_id).first()

            items_res.append({
                "id": q.id,
                "quotation_number": q.quotation_number or "DRAFT",
                "revision_number": q.current_revision_number,
                "created_at": q.created_at,
                "valid_until": valid_until,
                "status": q.status.value,
                "subtotal": float(rev.subtotal) if rev else 0.0,
                "discount_amount": float(rev.discount_amount) if rev else 0.0,
                "tax_amount": float(rev.tax_amount) if rev else 0.0,
                "grand_total": float(rev.grand_total) if rev else 0.0,
                "coupon_code": rev.coupon_code if rev else None,
                "agent_id": q.agent_id,
                "agent_name": agent_user.full_name if agent_user else "Agent",
                "is_own_quotation": (q.agent_id == current_user.id),
                "items": product_items
            })

        return {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "normalized_mobile": customer.normalized_mobile,
            "mobile_display": customer.mobile_display or customer.normalized_mobile,
            "email": customer.email,
            "address": customer.address,
            "quotations": items_res,
            "total": total,
            "page": page,
            "limit": limit
        }

    @staticmethod
    def reuse_quotation(
        db: Session,
        source_quotation_id: str,
        current_agent: User,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Creates a new DRAFT quotation from a historical quotation.
        Revalidates all items against the current product catalog and active prices.
        Revalidates coupons and reapplies current Admin GST policy.
        Never modifies the historical quotation.
        """
        source_quote = db.query(Quotation).filter(Quotation.id == source_quotation_id).first()
        if not source_quote:
            raise HTTPException(status_code=404, detail="Source quotation not found")

        latest_rev = source_quote.revisions[0] if source_quote.revisions else None
        if not latest_rev or not latest_rev.items:
            raise HTTPException(status_code=400, detail="Source quotation has no items to reuse.")

        # Revalidate products against current active catalog
        items_payload = []
        for itm in latest_rev.items:
            prod = db.query(Product).filter(Product.sku == itm.sku).first()
            if not prod:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product '{itm.product_name}' (SKU: {itm.sku}) is no longer in the catalog."
                )
            if not prod.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product '{prod.name}' (SKU: {prod.sku}) is deactivated and cannot be reused in a new quotation. Please choose a replacement product."
                )
            items_payload.append({
                "product_id": prod.id,
                "sku": prod.sku,
                "quantity": itm.quantity
            })

        # Revalidate coupon
        coupon_code = None
        coupon_warning = None
        if latest_rev.coupon_code:
            coupon_rec = db.query(Coupon).filter(Coupon.code == latest_rev.coupon_code.upper()).first()
            if coupon_rec and coupon_rec.is_active:
                coupon_code = coupon_rec.code
            else:
                coupon_warning = f"Coupon '{latest_rev.coupon_code}' from previous quotation is no longer active or has expired, and was omitted."

        # Calculate using current authorized prices & tax policy
        try:
            calc_result = PricingService.calculate_quotation(
                db=db,
                items_input=items_payload,
                coupon_code=coupon_code,
                agent_id=current_agent.id
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Ensure customer record is linked
        customer = CustomerService.get_or_create_customer(
            db=db,
            name=source_quote.customer_name,
            raw_mobile=source_quote.customer_mobile,
            email=source_quote.customer_email,
            address=source_quote.customer_address,
            agent_id=current_agent.id
        )

        # Create new DRAFT quotation with source reference
        new_quote = Quotation(
            quotation_number=None, # Fresh draft
            current_revision_number=0,
            agent_id=current_agent.id,
            customer_id=customer.id,
            source_quotation_id=source_quote.id,
            customer_name=source_quote.customer_name,
            customer_mobile=customer.normalized_mobile,
            customer_email=source_quote.customer_email,
            customer_address=source_quote.customer_address,
            status=QuotationStatus.DRAFT
        )
        db.add(new_quote)
        db.flush()

        new_rev = QuotationRevision(
            quotation_id=new_quote.id,
            revision_number=0,
            revision_label="Draft (Reused)",
            subtotal=calc_result["subtotal"],
            discount_amount=calc_result["discount_amount"],
            coupon_id=calc_result["coupon"].id if calc_result["coupon"] else None,
            coupon_code=calc_result["coupon_code"],
            tax_rate=calc_result["tax_rate"],
            tax_amount=calc_result["tax_amount"],
            grand_total=calc_result["grand_total"],
            is_superseded=False,
            created_by_id=current_agent.id
        )
        db.add(new_rev)
        db.flush()

        for itm_data in calc_result["items"]:
            db.add(QuotationItem(
                revision_id=new_rev.id,
                product_id=itm_data["product_id"],
                sku=itm_data["sku"],
                product_name=itm_data["product_name"],
                description=itm_data["description"],
                image_url=itm_data.get("image_url"),
                unit_price=itm_data["unit_price"],
                quantity=itm_data["quantity"],
                total_price=itm_data["total_price"]
            ))

        db.commit()

        if request:
            log_audit_event(
                db, current_agent, "REUSE_QUOTATION", "Quotation", new_quote.id,
                {
                    "source_quotation_id": source_quote.id,
                    "source_quotation_number": source_quote.quotation_number,
                    "customer_id": customer.id
                },
                request
            )

        source_display_num = source_quote.quotation_number or "Draft"
        return {
            "message": f"Successfully created new draft quotation from {source_display_num} with newly validated pricing and tax calculations.",
            "new_quotation_id": new_quote.id,
            "source_quotation_id": source_quote.id,
            "source_quotation_number": source_display_num,
            "customer_name": new_quote.customer_name,
            "customer_mobile": new_quote.customer_mobile,
            "items_count": len(calc_result["items"]),
            "subtotal": float(calc_result["subtotal"]),
            "discount_amount": float(calc_result["discount_amount"]),
            "tax_amount": float(calc_result["tax_amount"]),
            "grand_total": float(calc_result["grand_total"]),
            "coupon_applied": calc_result["coupon_code"],
            "coupon_warning": coupon_warning,
            "price_updated_notice": "Product prices and GST have been revalidated against current catalog settings."
        }
