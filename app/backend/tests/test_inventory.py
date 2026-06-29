from support import *


class InventoryTestCase(BackendTestCase):
    def test_order_inventory_reserves_available_stock_and_prints_only_shortage(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("INV-RESERVE")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=6,
            quantity_reserved=0,
        )
        order = Order(
            internal_order_number="T-ORDER-1",
            platform_id=platform.id,
            external_order_id="EXT-1",
            order_date=datetime.now(timezone.utc),
            total_amount=129.50,
            currency="EUR",
        )
        self.db.add_all([inventory, order])
        self.db.commit()
        order_item = OrderItem(
            order_id=order.id,
            sku=variant.sku,
            quantity_ordered=10,
            unit_sale_price=12.95,
        )
        self.db.add(order_item)
        self.db.commit()

        result = process_order_inventory(order.id, self.db)

        self.db.refresh(order_item)
        self.db.refresh(inventory)
        self.assertEqual(result["order"]["status"], "deels_te_printen")
        self.assertEqual(order_item.quantity_from_inventory, 6)
        self.assertEqual(order_item.quantity_to_print, 4)
        self.assertEqual(order_item.inventory_status, "deels_op_voorraad")
        self.assertEqual(inventory.quantity_reserved, 6)
        movement = self.db.scalar(select(InventoryMovement))
        self.assertEqual(movement.movement_type, "gereserveerd_voor_order")
        self.assertEqual(movement.quantity, 6)
        self.assertEqual(movement.quantity_on_hand_before, 6)
        self.assertEqual(movement.quantity_on_hand_after, 6)
        self.assertEqual(movement.quantity_reserved_before, 0)
        self.assertEqual(movement.quantity_reserved_after, 6)
        self.assertEqual(movement.free_stock_before, 6)
        self.assertEqual(movement.free_stock_after, 0)
        self.assertEqual(movement.source, "order_inventory_check")

    def test_reprocessing_order_inventory_does_not_double_reserve(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("INV-REPROCESS")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=6,
            quantity_reserved=0,
        )
        order = Order(
            internal_order_number="T-ORDER-REPROCESS",
            platform_id=platform.id,
            external_order_id="EXT-REPROCESS",
            order_date=datetime.now(timezone.utc),
            total_amount=129.50,
            currency="EUR",
        )
        self.db.add_all([inventory, order])
        self.db.commit()
        order_item = OrderItem(order_id=order.id, sku=variant.sku, quantity_ordered=4, unit_sale_price=12.95)
        self.db.add(order_item)
        self.db.commit()

        process_order_inventory(order.id, self.db)
        process_order_inventory(order.id, self.db)

        self.db.refresh(inventory)
        self.db.refresh(order_item)
        movements = self.db.scalars(select(InventoryMovement).order_by(InventoryMovement.id)).all()
        self.assertEqual(inventory.quantity_reserved, 4)
        self.assertEqual(order_item.quantity_from_inventory, 4)
        self.assertEqual(order_item.quantity_to_print, 0)
        self.assertEqual(
            [(movement.movement_type, movement.quantity) for movement in movements],
            [
                ("gereserveerd_voor_order", 4),
                ("reservering_vrijgegeven", 4),
                ("gereserveerd_voor_order", 4),
            ],
        )
        self.assertEqual(movements[-1].free_stock_after, 2)

    def test_inventory_adjustment_cannot_make_free_stock_negative(self) -> None:
        product, variant = self.make_product_variant("INV-NEGATIVE")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=4,
            quantity_reserved=3,
        )
        self.db.add(inventory)
        self.db.commit()

        with self.assertRaises(HTTPException):
            adjust_inventory_service(self.db, inventory, -2)

        self.db.refresh(inventory)
        movements = self.db.scalars(select(InventoryMovement)).all()
        self.assertEqual(inventory.quantity_on_hand, 4)
        self.assertEqual(inventory.quantity_reserved, 3)
        self.assertEqual(movements, [])
