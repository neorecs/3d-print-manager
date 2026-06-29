from support import *


class PlanningTestCase(BackendTestCase):
    def test_print_result_sends_extra_successes_to_inventory_and_failed_to_movements(self) -> None:
        product, variant = self.make_product_variant("PRINT-RESULT")
        print_job = PrintJob(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_needed=4,
            quantity_planned=12,
            status="nieuw",
        )
        self.db.add(print_job)
        self.db.commit()

        result = complete_print_job(
            print_job.id,
            PrintJobComplete(quantity_succeeded=11, quantity_failed=1, quantity_to_order=4),
            self.db,
        )

        inventory = self.db.scalar(select(ProductInventory).where(ProductInventory.product_variant_id == variant.id))
        movements = self.db.scalars(select(InventoryMovement).order_by(InventoryMovement.id)).all()
        self.assertEqual(result["quantity_to_inventory"], 7)
        self.assertEqual(result["status"], "deels_mislukt")
        self.assertEqual(inventory.quantity_on_hand, 7)
        self.assertEqual(
            [(item.movement_type, item.quantity) for item in movements],
            [("print_gereed", 7), ("afgekeurd", 1)],
        )
        self.assertEqual(movements[0].source, "print_result")
        self.assertEqual(movements[0].quantity_on_hand_before, 0)
        self.assertEqual(movements[0].quantity_on_hand_after, 7)
        self.assertEqual(movements[0].free_stock_after, 7)

    def test_stock_recommendation_uses_sales_safety_stock_and_free_stock(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("STOCK-ADVICE")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            color=variant.color,
            material=variant.material,
            quantity_on_hand=3,
            quantity_reserved=0,
        )
        order = Order(
            internal_order_number="T-ORDER-2",
            platform_id=platform.id,
            external_order_id="EXT-2",
            order_date=datetime.now(timezone.utc),
            total_amount=129.50,
            currency="EUR",
        )
        self.db.add_all([inventory, order])
        self.db.commit()
        self.db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_variant_id=variant.id,
                sku=variant.sku,
                quantity_ordered=10,
                unit_sale_price=12.95,
            )
        )
        self.db.commit()

        result = generate_stock_recommendations(
            StockRecommendationGenerate(period_days=7, safety_stock=2, weeks_ahead=1),
            self.db,
        )

        recommendation = self.db.scalar(select(StockRecommendation))
        self.assertEqual(result["generated_count"], 1)
        self.assertEqual(recommendation.current_free_stock, 3)
        self.assertEqual(recommendation.expected_sales, 10)
        self.assertEqual(recommendation.recommended_stock_level, 12)
        self.assertEqual(recommendation.recommended_print_quantity, 9)
        self.assertIn("Gemiddelde weekverkoop", recommendation.reason)

    def test_adjusted_stock_recommendation_converts_adjusted_quantity_to_print_job(self) -> None:
        product, variant = self.make_product_variant("STOCK-ADJUST")
        recommendation = StockRecommendation(
            product_id=product.id,
            product_variant_id=variant.id,
            current_free_stock=3,
            expected_sales=10,
            safety_stock=2,
            recommended_stock_level=12,
            recommended_print_quantity=9,
            reason="Initieel advies.",
            status="nieuw",
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)

        updated = update_stock_recommendation(
            recommendation.id,
            StockRecommendationUpdate(
                safety_stock=4,
                recommended_print_quantity=6,
                reason="Handmatig lager gezet.",
            ),
            self.db,
        )
        print_job = convert_stock_recommendation(recommendation.id, self.db)

        self.assertEqual(updated["status"], "aangepast")
        self.assertEqual(updated["recommended_print_quantity"], 6)
        self.assertEqual(print_job["quantity_needed"], 6)
        self.assertEqual(print_job["quantity_to_inventory"], 6)

    def test_batch_suggestions_group_open_jobs_by_material_and_color(self) -> None:
        product, variant = self.make_product_variant("BATCH-ADVICE")
        other_product, other_variant = self.make_product_variant("BATCH-OTHER")
        self.db.add_all(
            [
                PrintJob(
                    product_id=product.id,
                    product_variant_id=variant.id,
                    color="rood",
                    material="PLA",
                    quantity_needed=4,
                    quantity_planned=6,
                    quantity_to_order=4,
                    quantity_to_inventory=2,
                    estimated_print_time_minutes=180,
                    estimated_filament_grams=120,
                    status="nieuw",
                ),
                PrintJob(
                    product_id=other_product.id,
                    product_variant_id=other_variant.id,
                    color="rood",
                    material="PLA",
                    quantity_needed=2,
                    quantity_planned=2,
                    quantity_to_order=2,
                    quantity_to_inventory=0,
                    estimated_print_time_minutes=60,
                    estimated_filament_grams=40,
                    status="gepland",
                ),
                PrintJob(
                    product_id=product.id,
                    product_variant_id=variant.id,
                    color="zwart",
                    material="PETG",
                    quantity_needed=1,
                    quantity_planned=1,
                    estimated_print_time_minutes=30,
                    estimated_filament_grams=20,
                    status="verwerkt",
                ),
            ]
        )
        self.db.commit()

        suggestions = suggest_print_batches(self.db)

        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["material"], "PLA")
        self.assertEqual(suggestion["color"], "rood")
        self.assertEqual(suggestion["job_count"], 2)
        self.assertEqual(suggestion["quantity_planned"], 8)
        self.assertEqual(suggestion["quantity_to_order"], 6)
        self.assertEqual(suggestion["quantity_to_inventory"], 2)
        self.assertEqual(suggestion["estimated_total_print_time_minutes"], 240)
        self.assertEqual(suggestion["estimated_total_filament_grams"], 160)
        self.assertIn("hetzelfde materiaal", suggestion["reason"])
