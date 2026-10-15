from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from app.models.product import Product
from app.models.coupon import Coupon, CouponDiscountType
from app.models.settings import TaxSettings, TaxPricingPolicy
from app.schemas.quotation import QuotationItemInput

def round_curr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PricingService:
    @staticmethod
    def calculate_quotation(
        db: Session,
        items_input: List[QuotationItemInput],
        coupon_code: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recalculates all product prices, line totals, discounts, taxes and grand total server-side.
        Never trusts client-side prices or totals.
        """
        # Fetch current active tax settings
        tax_setting = db.query(TaxSettings).filter(TaxSettings.is_active == True).order_by(TaxSettings.version.desc()).first()
        gst_rate = tax_setting.gst_rate if tax_setting else Decimal("18.00")
        pricing_policy = tax_setting.pricing_policy if tax_setting else TaxPricingPolicy.EXCLUSIVE

        calculated_items = []
        subtotal = Decimal("0.00")
        categories_in_quote = set()

        for item_in in items_input:
            product = db.query(Product).filter(Product.id == item_in.product_id).first()
            if not product:
                raise ValueError(f"Product ID '{item_in.product_id}' not found.")
            if not product.is_active:
                raise ValueError(f"Product '{product.name}' ({product.sku}) is archived and cannot be added.")
            if item_in.quantity <= 0:
                raise ValueError(f"Invalid quantity {item_in.quantity} for product '{product.name}'.")

            unit_price = Decimal(str(product.base_price))
            line_total = round_curr(unit_price * Decimal(item_in.quantity))
            subtotal += line_total
            categories_in_quote.add(product.category)

            calculated_items.append({
                "product_id": product.id,
                "sku": product.sku,
                "product_name": product.name,
                "description": product.description,
                "unit_price": unit_price,
                "quantity": item_in.quantity,
                "total_price": line_total
            })

        # Process Coupon if present
        discount_amount = Decimal("0.00")
        applied_coupon = None

        if coupon_code:
            coupon_clean = coupon_code.strip().upper()
            now = datetime.now(timezone.utc)
            coupon = db.query(Coupon).filter(Coupon.code == coupon_clean, Coupon.is_active == True).first()
            if not coupon:
                raise ValueError(f"Coupon code '{coupon_clean}' is invalid or inactive.")

            if coupon.start_date and now < coupon.start_date.replace(tzinfo=timezone.utc):
                raise ValueError(f"Coupon '{coupon_clean}' is not yet valid.")
            if coupon.end_date and now > coupon.end_date.replace(tzinfo=timezone.utc):
                raise ValueError(f"Coupon '{coupon_clean}' has expired.")
            if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                raise ValueError(f"Coupon '{coupon_clean}' usage limit has been reached.")
            if subtotal < coupon.min_subtotal:
                raise ValueError(f"Coupon '{coupon_clean}' requires a minimum subtotal of ₹{coupon.min_subtotal}.")

            # Category restriction check
            if coupon.eligible_categories:
                eligible_cats = json.loads(coupon.eligible_categories)
                if not any(cat in eligible_cats for cat in categories_in_quote):
                    raise ValueError(f"Coupon '{coupon_clean}' is not applicable to products in this quotation.")

            # Agent restriction check
            if coupon.eligible_agent_ids and agent_id:
                eligible_agents = json.loads(coupon.eligible_agent_ids)
                if agent_id not in eligible_agents:
                    raise ValueError(f"Coupon '{coupon_clean}' is not authorized for your account.")

            # Calculate discount
            if coupon.discount_type == CouponDiscountType.FIXED:
                discount_amount = Decimal(str(coupon.discount_value))
            elif coupon.discount_type == CouponDiscountType.PERCENTAGE:
                discount_amount = subtotal * (Decimal(str(coupon.discount_value)) / Decimal("100"))
                if coupon.max_discount and discount_amount > Decimal(str(coupon.max_discount)):
                    discount_amount = Decimal(str(coupon.max_discount))

            # Discount cannot exceed subtotal
            if discount_amount > subtotal:
                discount_amount = subtotal

            discount_amount = round_curr(discount_amount)
            applied_coupon = coupon

        # Calculate GST and Grand Total
        net_taxable = subtotal - discount_amount
        if net_taxable < Decimal("0.00"):
            net_taxable = Decimal("0.00")

        if pricing_policy == TaxPricingPolicy.EXCLUSIVE:
            tax_amount = round_curr(net_taxable * (gst_rate / Decimal("100")))
            grand_total = net_taxable + tax_amount
        else: # INCLUSIVE
            tax_amount = round_curr(net_taxable - (net_taxable / (Decimal("1") + gst_rate / Decimal("100"))))
            grand_total = net_taxable

        return {
            "items": calculated_items,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "coupon": applied_coupon,
            "coupon_code": applied_coupon.code if applied_coupon else None,
            "tax_rate": gst_rate,
            "tax_amount": tax_amount,
            "tax_policy": pricing_policy.value,
            "grand_total": grand_total
        }
