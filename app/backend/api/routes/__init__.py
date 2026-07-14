from fastapi import APIRouter

from api.routes import accounting, ai, auth, bambu, health, inventory, orders, planning, platforms, products, system, uploads
from api.routes.orders import process_order_inventory
from api.routes.planning import (
    complete_print_job,
    convert_stock_recommendation,
    generate_stock_recommendations,
    suggest_print_batches,
    update_stock_recommendation,
)
from api.routes.products import publish_product_publication
from publishing.service import validate_publication_record


router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(ai.router)
router.include_router(accounting.router)
router.include_router(bambu.router)
router.include_router(platforms.router)
router.include_router(products.router)
router.include_router(system.router)
router.include_router(uploads.router)
router.include_router(orders.router)
router.include_router(inventory.router)
router.include_router(planning.router)


__all__ = [
    "router",
    "complete_print_job",
    "convert_stock_recommendation",
    "generate_stock_recommendations",
    "process_order_inventory",
    "publish_product_publication",
    "suggest_print_batches",
    "update_stock_recommendation",
    "validate_publication_record",
]
