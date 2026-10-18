from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.admin.users import router as admin_users_router
from app.api.v1.admin.products import router as admin_products_router
from app.api.v1.admin.prices import router as admin_prices_router
from app.api.v1.admin.coupons import router as admin_coupons_router
from app.api.v1.admin.settings import router as admin_settings_router
from app.api.v1.admin.quotations import router as admin_quotations_router
from app.api.v1.admin.payments import router as admin_payments_router
from app.api.v1.admin.orders import router as admin_orders_router
from app.api.v1.admin.dashboard import router as admin_dashboard_router

from app.api.v1.agent.products import router as agent_products_router
from app.api.v1.agent.quotations import router as agent_quotations_router
from app.api.v1.agent.payments import router as agent_payments_router
from app.api.v1.agent.dashboard import router as agent_dashboard_router
from app.api.v1.customers import router as customers_router

api_router = APIRouter()

# Auth
api_router.include_router(auth_router)

# Customers & Quotation History
api_router.include_router(customers_router)

# Admin
api_router.include_router(admin_dashboard_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_products_router)
api_router.include_router(admin_prices_router)
api_router.include_router(admin_coupons_router)
api_router.include_router(admin_settings_router)
api_router.include_router(admin_quotations_router)
api_router.include_router(admin_payments_router)
api_router.include_router(admin_orders_router)

# Agent
api_router.include_router(agent_dashboard_router)
api_router.include_router(agent_products_router)
api_router.include_router(agent_quotations_router)
api_router.include_router(agent_payments_router)
