from support import *
from api.routes.planning import accept_stock_recommendation, mark_print_job_bambu_studio_opened
from models import BambuPrinter
from schemas.common import PrintJobBambuStudioOpen


class PlanningTestCase(BackendTestCase):
    def test_studio_handoff_without_printer_is_repeatable_for_source_model(self) -> None:
        product, variant = self.make_product_variant("STUDIO-SOURCE")
        product.print_file_path = "prints/model.stl"
        job = PrintJob(product_id=product.id, product_variant_id=variant.id,
                       quantity_needed=2, quantity_planned=2, status="nieuw")
        self.db.add(job)
        self.db.commit()
        payload = PrintJobBambuStudioOpen(product_id=product.id, product_variant_id=variant.id)
        for _ in range(2):
            result = mark_print_job_bambu_studio_opened(job.id, payload, self.db)
            self.assertEqual(result["status"], "gepland")
            self.assertIsNone(result["printer_id"])
            self.assertIsNotNone(result["bambu_studio_opened_at"])
        self.assertEqual(len(self.db.scalars(select(PrintJob)).all()), 1)
        self.assertEqual(self.db.scalars(select(InventoryMovement)).all(), [])

    def test_studio_handoff_does_not_change_started_or_closed_job(self) -> None:
        product, variant = self.make_product_variant("STUDIO-CLOSED")
        for status in ("bezig", "verwerkt", "geannuleerd", "geprint", "deels_mislukt"):
            with self.subTest(status=status):
                job = PrintJob(product_id=product.id, product_variant_id=variant.id,
                               quantity_needed=1, quantity_planned=1, status=status)
                self.db.add(job)
                self.db.commit()
                with self.assertRaises(HTTPException) as raised:
                    mark_print_job_bambu_studio_opened(job.id, PrintJobBambuStudioOpen(
                        product_id=product.id, product_variant_id=variant.id), self.db)
                self.assertEqual(raised.exception.status_code, 409)
                self.assertEqual(job.status, status)
                self.assertIsNone(job.bambu_studio_opened_at)

    def test_studio_handoff_rejects_wrong_product(self) -> None:
        product, variant = self.make_product_variant("STUDIO-WRONG")
        job = PrintJob(product_id=product.id, product_variant_id=variant.id,
                       quantity_needed=1, quantity_planned=1, status="nieuw")
        self.db.add(job)
        self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            mark_print_job_bambu_studio_opened(job.id, PrintJobBambuStudioOpen(
                product_id=product.id + 1, product_variant_id=variant.id), self.db)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(job.status, "nieuw")
        self.assertIsNone(job.bambu_studio_opened_at)

    def test_opening_job_in_bambu_studio_assigns_printer_and_plans_job(self) -> None:
        product, variant = self.make_product_variant("STUDIO-PLAN")
        printer = BambuPrinter(name="P2S Productie", model="P2S", host="10.0.0.20", active=True)
        job = PrintJob(
            product_id=product.id,
            product_variant_id=variant.id,
            quantity_needed=2,
            quantity_planned=2,
            status="nieuw",
        )
        self.db.add_all([printer, job])
        self.db.commit()
        self.db.refresh(printer)
        self.db.refresh(job)

        result = mark_print_job_bambu_studio_opened(
            job.id,
            PrintJobBambuStudioOpen(
                printer_id=printer.id,
                product_id=product.id,
                product_variant_id=variant.id,
            ),
            self.db,
        )

        self.assertEqual(result["printer_id"], printer.id)
        self.assertEqual(result["status"], "gepland")
        self.assertIsNotNone(result["bambu_studio_opened_at"])

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

    def test_recommendation_rechecks_stock_and_cannot_create_two_print_jobs(self) -> None:
        product, variant = self.make_product_variant("STOCK-RECHECK")
        inventory = ProductInventory(
            product_id=product.id,
            product_variant_id=variant.id,
            quantity_on_hand=10,
            quantity_reserved=0,
        )
        recommendation = StockRecommendation(
            product_id=product.id,
            product_variant_id=variant.id,
            current_free_stock=3,
            expected_sales=10,
            safety_stock=2,
            recommended_stock_level=12,
            recommended_print_quantity=9,
            reason="Oud advies.",
            status="nieuw",
        )
        self.db.add_all([inventory, recommendation])
        self.db.commit()

        accepted = accept_stock_recommendation(recommendation.id, self.db)
        print_job = convert_stock_recommendation(recommendation.id, self.db)

        self.assertEqual(accepted["current_free_stock"], 10)
        self.assertEqual(accepted["recommended_print_quantity"], 2)
        self.assertEqual(print_job["quantity_needed"], 2)
        self.assertEqual(len(self.db.scalars(select(PrintJob)).all()), 1)
        with self.assertRaises(HTTPException) as raised:
            convert_stock_recommendation(recommendation.id, self.db)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(self.db.scalars(select(PrintJob)).all()), 1)

    def test_cancelled_orders_do_not_generate_stock_advice(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("STOCK-CANCELLED")
        order = Order(
            internal_order_number="T-CANCELLED",
            platform_id=platform.id,
            external_order_id="EXT-CANCELLED",
            order_date=datetime.now(timezone.utc),
            status="geannuleerd",
        )
        self.db.add(order)
        self.db.commit()
        self.db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            quantity_ordered=20,
            unit_sale_price=10,
        ))
        self.db.commit()

        result = generate_stock_recommendations(
            StockRecommendationGenerate(period_days=30, safety_stock=2, weeks_ahead=1),
            self.db,
        )

        self.assertEqual(result["generated_count"], 0)
        self.assertEqual(self.db.scalars(select(StockRecommendation)).all(), [])

    def test_regeneration_preserves_an_accepted_recommendation(self) -> None:
        platform = self.make_platform()
        product, variant = self.make_product_variant("STOCK-ACCEPTED")
        order = Order(
            internal_order_number="T-ACCEPTED",
            platform_id=platform.id,
            external_order_id="EXT-ACCEPTED",
            order_date=datetime.now(timezone.utc),
        )
        recommendation = StockRecommendation(
            product_id=product.id,
            product_variant_id=variant.id,
            current_free_stock=0,
            expected_sales=4,
            safety_stock=3,
            recommended_stock_level=7,
            recommended_print_quantity=7,
            reason="Door gebruiker geaccepteerd advies.",
            status="geaccepteerd",
        )
        self.db.add_all([order, recommendation])
        self.db.commit()
        self.db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            quantity_ordered=20,
            unit_sale_price=10,
        ))
        self.db.commit()

        generate_stock_recommendations(
            StockRecommendationGenerate(period_days=30, safety_stock=9, weeks_ahead=2),
            self.db,
        )
        self.db.refresh(recommendation)

        self.assertEqual(recommendation.status, "geaccepteerd")
        self.assertEqual(recommendation.recommended_print_quantity, 7)
        self.assertEqual(recommendation.reason, "Door gebruiker geaccepteerd advies.")

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
