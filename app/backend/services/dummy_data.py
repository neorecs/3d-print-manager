from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    FilamentSpool,
    Order,
    OrderItem,
    Platform,
    PrintBatch,
    PrintJob,
    Product,
    ProductInventory,
    ProductMedia,
    ProductPlatformPublication,
    ProductTag,
    ProductVariant,
    StockRecommendation,
    TrendSnapshot,
)


def seed_dummy_data(db: Session) -> None:
    if db.scalar(select(Product).limit(1)):
        return

    etsy = Platform(name="Etsy", type="etsy", api_base_url="https://api.etsy.com", active=True)
    shopify = Platform(name="Shopify", type="shopify", api_base_url="https://example.myshopify.com", active=True)
    db.add_all([etsy, shopify])
    db.flush()

    product = Product(
        name="Dumpling Rood",
        internal_title="3D geprinte dumpling - rood",
        short_description="Decoratieve rode 3D-geprinte dumpling.",
        long_description="Een compacte decoratieve dumpling, geschikt als cadeau of bureau-accessoire.",
        sales_description="Leuke rode 3D-geprinte dumpling voor verzamelaars en cadeaus.",
        seo_title="Rode 3D-geprinte dumpling",
        seo_description="Decoratieve rode dumpling, gemaakt met PLA.",
        product_type="Decoratie",
        internal_category="Figuren",
        status="klaar_voor_publicatie",
    )
    db.add(product)
    db.flush()

    variant = ProductVariant(
        product_id=product.id,
        variant_name="Rood PLA",
        sku="DUMP-RED-PLA",
        color="Rood",
        material="PLA",
        print_file_path="/print-files/dumpling-red.3mf",
        estimated_print_time_minutes=55,
        estimated_filament_grams=22,
        weight_grams=24,
        length_mm=45,
        width_mm=38,
        height_mm=34,
        default_sale_price=9.95,
        cost_price=1.35,
    )
    db.add(variant)
    db.flush()

    db.add_all(
        [
            ProductTag(product_id=product.id, tag="dumpling"),
            ProductTag(product_id=product.id, tag="3d print"),
            ProductMedia(
                product_id=product.id,
                file_path="/media/products/dumpling-red-main.jpg",
                alt_text="Rode 3D-geprinte dumpling",
                sort_order=1,
                is_primary=True,
            ),
            ProductPlatformPublication(
                product_id=product.id,
                platform_id=etsy.id,
                publication_status="synchronisatie_nodig",
                platform_title="Red 3D Printed Dumpling",
                platform_description="Cute red 3D printed dumpling.",
                platform_category="Home Decor",
                platform_tags="dumpling,3d print,gift",
                platform_price_override=10.95,
            ),
            ProductPlatformPublication(
                product_id=product.id,
                platform_id=shopify.id,
                publication_status="niet_gepubliceerd",
                platform_title="Rode 3D-geprinte dumpling",
                platform_category="Decoratie",
                platform_tags="dumpling,3d print",
            ),
        ]
    )

    inventory = ProductInventory(
        product_id=product.id,
        product_variant_id=variant.id,
        color="Rood",
        material="PLA",
        quantity_on_hand=6,
        quantity_reserved=2,
        minimum_stock_level=4,
        location="Bak A1",
    )
    db.add(inventory)

    filament = FilamentSpool(
        brand="Bambu Lab",
        material="PLA",
        color="Rood",
        initial_weight_grams=1000,
        remaining_weight_grams=640,
        purchase_price=22.99,
        price_per_gram=0.023,
        minimum_remaining_grams=150,
        location="Rek 1",
    )
    db.add(filament)

    order = Order(
        internal_order_number="ORD-2026-0001",
        platform_id=etsy.id,
        external_order_id="ETSY-DEMO-1001",
        customer_name="Demo klant",
        customer_email="demo@example.com",
        order_date=datetime.now(timezone.utc),
        total_amount=39.80,
        currency="EUR",
        status="deels_te_printen",
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_variant_id=variant.id,
        external_order_item_id="ETSY-LINE-1",
        sku=variant.sku,
        quantity_ordered=10,
        quantity_from_inventory=4,
        quantity_to_print=6,
        unit_sale_price=9.95,
        inventory_status="deels_op_voorraad",
    )
    db.add(order_item)
    db.flush()

    print_job = PrintJob(
        order_item_id=order_item.id,
        product_id=product.id,
        product_variant_id=variant.id,
        color="Rood",
        material="PLA",
        quantity_needed=6,
        quantity_planned=12,
        quantity_to_order=6,
        quantity_to_inventory=6,
        estimated_print_time_minutes=660,
        estimated_filament_grams=264,
        status="gepland",
    )
    db.add(print_job)
    db.flush()

    db.add_all(
        [
            PrintBatch(
                batch_name="Batch demo rood PLA",
                material="PLA",
                color="Rood",
                estimated_total_print_time_minutes=660,
                estimated_total_filament_grams=264,
                status="gepland",
            ),
            TrendSnapshot(
                product_id=product.id,
                product_variant_id=variant.id,
                period_days=30,
                quantity_sold=40,
                average_weekly_sales=10,
                revenue=398,
                estimated_profit=285,
            ),
            StockRecommendation(
                product_id=product.id,
                product_variant_id=variant.id,
                current_free_stock=4,
                expected_sales=10,
                safety_stock=2,
                recommended_stock_level=12,
                recommended_print_quantity=8,
                reason="Gemiddeld 10 verkopen per week, plus 2 veiligheidsvoorraad, min 4 vrije voorraad.",
                status="nieuw",
            ),
        ]
    )

    db.commit()
