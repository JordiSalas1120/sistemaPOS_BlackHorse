from fastapi import APIRouter

from src.infrastructure.api.v1.endpoints.products import categories_router, router as products_router
from src.infrastructure.api.v1.endpoints.inventory import router as inventory_router
from src.infrastructure.api.v1.endpoints.clients import router as clients_router
from src.infrastructure.api.v1.endpoints.sales import router as sales_router
from src.infrastructure.api.v1.endpoints.price_rules import router as price_rules_router
from src.infrastructure.api.v1.endpoints.exports import router as exports_router
from src.infrastructure.api.v1.endpoints.workshop import router as workshop_router
from src.infrastructure.api.v1.endpoints.production_orders import router as production_router

api_router = APIRouter()

api_router.include_router(categories_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(clients_router)
api_router.include_router(sales_router)
api_router.include_router(price_rules_router)
api_router.include_router(exports_router)
api_router.include_router(workshop_router)
api_router.include_router(production_router)
