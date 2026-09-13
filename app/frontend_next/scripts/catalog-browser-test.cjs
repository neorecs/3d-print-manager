const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

async function listen(server) {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${server.address().port}`;
}

async function main() {
  let creates = 0, uploads = 0, mediaFails = false, printerFails = true, orderProcesses = 0, completedPayload = null;
  const overviewRequests = [];
  const products = [
    { id: 1, name: "Telefoonhouder", internal_title: "Telefoonhouder", active: true, status: "klaar_voor_publicatie", print_file_path: "model.stl" },
    { id: 2, name: "Archiefproduct", active: false, status: "gearchiveerd" },
  ];
  const variants = [{ id: 1, product_id: 1, variant_name: "Rood PLA", sku: "HOUDER-ROOD", color: "rood", material: "PLA", active: true }];
  const orders = [{ id: 1, internal_order_number: "WEB-TEST-1", external_order_id: "WEB-TEST-1", platform_id: 1, customer_name: "Testklant", total_amount: 25.9, currency: "EUR", status: "nieuw", payment_status: "betaald" }];
  const orderItems = [{ id: 1, order_id: 1, product_id: 1, product_variant_id: 1, sku: "HOUDER-ROOD", quantity_ordered: 2, quantity_from_inventory: 0, quantity_to_print: 0, inventory_status: "niet_op_voorraad", unit_sale_price: 12.95 }];
  const printJobs = [];
  const accountingSales = [];
  const recommendations = [
    { id: 1, product_id: 1, product_variant_id: 1, product: "Telefoonhouder", variant: "Rood PLA", current_free_stock: 2, expected_sales: 6, safety_stock: 2, recommended_stock_level: 8, recommended_print_quantity: 6, reason: "Berekend over 30 dagen op basis van gemiddelde weekverkoop en vrije voorraad.", status: "nieuw", updated_at: "2026-09-13T08:00:00Z" },
    { id: 2, product_id: 1, product_variant_id: 1, product: "Telefoonhouder", variant: "Rood PLA", current_free_stock: 4, expected_sales: 6, safety_stock: 2, recommended_stock_level: 8, recommended_print_quantity: 4, reason: "Eerder omgezet naar een printtaak.", status: "omgezet_naar_printtaak", updated_at: "2026-09-12T08:00:00Z" },
  ];
  const fixture = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://fixture");
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const reply = (data, status = 200) => { res.writeHead(status, { "Content-Type": "application/json" }); res.end(JSON.stringify(data)); };
    if (url.pathname === "/products/with-variant") {
      creates++;
      const payload = JSON.parse(Buffer.concat(chunks));
      assert.equal(payload.first_variant, null);
      products.push({ ...payload, id: 3 });
      return reply({ id: 3 });
    }
    if (url.pathname === "/products/3/print-file/upload") {
      uploads++;
      return uploads === 1 ? reply({ detail: "Testupload mislukt" }, 503) : reply({ ok: true });
    }
    if (url.pathname === "/orders/1/process" && req.method === "POST") {
      orderProcesses++;
      orders[0].status = "ingepland";
      orderItems[0].quantity_to_print = 2;
      if (!printJobs.length) printJobs.push({ id: 1, order_item_id: 1, product_id: 1, product_variant_id: 1, color: "rood", material: "PLA", quantity_needed: 2, quantity_planned: 2, quantity_succeeded: null, quantity_failed: null, quantity_to_order: 2, quantity_to_inventory: 0, estimated_print_time_minutes: 60, estimated_filament_grams: 40, status: "nieuw" });
      if (!accountingSales.length) accountingSales.push({ id: 1, order_id: 1, invoice_number: "WEB-TEST-1", gross_amount: 25.9, net_amount: 21.4, vat_amount: 4.5, status: "concept" });
      return reply({ status: "processed", message: "Order verwerkt: voorraad en printplanning zijn bijgewerkt. Verkoopboeking is vastgelegd." });
    }
    if (url.pathname === "/print-jobs/1/complete" && req.method === "POST") {
      completedPayload = JSON.parse(Buffer.concat(chunks));
      Object.assign(printJobs[0], completedPayload, { status: completedPayload.quantity_failed ? "deels_mislukt" : "geprint" });
      return reply({ status: "completed" });
    }
    if (url.pathname === "/stock-recommendations/1/accept" && req.method === "POST") {
      recommendations[0].status = "geaccepteerd";
      return reply(recommendations[0]);
    }
    if (url.pathname === "/orders/1") return reply({ ...orders[0], items: orderItems });
    if (url.pathname === "/products/overview") {
      overviewRequests.push(url.search);
      const view = url.searchParams.get("view") || "actief";
      const rows = products
        .filter((product) => view === "alle" || (view === "archief" ? !product.active || product.status === "gearchiveerd" : product.active && product.status !== "gearchiveerd"))
        .map((product) => ({ product, variants: variants.filter((item) => item.product_id === product.id), inventory: [], publications: [] }));
      return reply({ rows, metrics: { products: rows.length, variants: rows.flatMap((row) => row.variants).length, low_stock: 0, published: 0, margin_potential: 0 }, page: 1, page_size: 20, page_count: 1, total: rows.length, view });
    }
    if (url.pathname === "/orders/overview") {
      const status = url.searchParams.get("status") || "alle";
      const filtered = orders.filter((order) => status === "alle" || order.status === status);
      return reply({
        orders: filtered,
        order_items: orderItems.filter((item) => filtered.some((order) => order.id === item.order_id)),
        platforms: [{ id: 1, name: "Testkanaal", type: "etsy", active: true }],
        print_jobs: printJobs,
        import_logs: [],
        metrics: { total: orders.length, new: orders.filter((order) => order.status === "nieuw").length, paid: 1, production: 0, packed: 0, shipped: 0, cancelled: 0, revenue: 25.9 },
        page: 1,
        page_size: 25,
        page_count: 1,
        total: filtered.length,
        status,
      });
    }
    if (url.pathname === "/orders") return reply(orders);
    if (url.pathname === "/order-items") return reply(orderItems);
    if (url.pathname === "/orders/import-logs") return reply([]);
    if (url.pathname === "/filament") return reply([{ id: 1, brand: "Bambu Lab", material: "PLA", color: "Rood", initial_weight_grams: 1000, remaining_weight_grams: 640, purchase_price: 24.99, price_per_gram: 0.025, minimum_remaining_grams: 100, location: "Rek A", active: true }]);
    if (url.pathname === "/sales-markets") return reply([{ id: 1, country_code: "NL", country_name: "Nederland", primary_language: "nl", additional_languages: "", currency: "EUR", active: true }]);
    if (url.pathname === "/platforms") return reply([{ id: 1, name: "Testkanaal", type: "etsy", active: true }]);
    if (url.pathname === "/platforms/1/connector-status") return reply({ platform_id: 1, platform: "Testkanaal", platform_type: "etsy", mode: "teststand", ready_for_live: false, missing_credentials: ["API-sleutel"] });
    if (url.pathname === "/product-variants") return reply(variants);
    if (url.pathname === "/print-jobs") return reply(printJobs);
    if (url.pathname === "/print-batches") return reply([]);
    if (url.pathname === "/accounting/sales") return reply(accountingSales);
    if (url.pathname === "/analytics/sales-trends") return reply([{ product_id: 1, product_variant_id: 1, product: "Telefoonhouder", quantity_sold: 6, revenue: 77.7, estimated_profit: 35.5 }]);
    if (url.pathname === "/analytics/top-products") return reply([{ product_id: 1, product: "Telefoonhouder", quantity_sold: 6, revenue: 77.7, estimated_profit: 35.5 }]);
    if (url.pathname === "/analytics/top-colors") return reply([{ color: "rood", quantity_sold: 6, revenue: 77.7, estimated_profit: 35.5 }]);
    if (url.pathname === "/analytics/top-materials") return reply([{ material: "PLA", quantity_sold: 6, revenue: 77.7, estimated_profit: 35.5 }]);
    if (url.pathname === "/stock-recommendations") return reply(recommendations);
    if (url.pathname === "/cost-settings") return reply([]);
    if (url.pathname === "/system/readiness") return reply({
      connectors_live_mode: false, live_calls_blocked: true,
      credential_encryption_configured: true, internal_api_configured: true, session_signing_configured: true,
      database_configured: true, database_reachable: true, upload_storage_writable: true, upload_backup_configured: true,
      database_backup_recent: true, upload_backup_recent: true, restore_test_recent: true,
      database_backup_last_success: "2026-09-13T07:00:00Z", upload_backup_last_success: "2026-09-13T07:05:00Z", restore_test_last_success: "2026-09-12T09:00:00Z",
      auth_enabled: true, auth_backend_login: true, secure_cookie_enabled: false,
      ai_enabled: false, ai_configured: false, openai_model: "gpt-5.4-mini",
      platform_subscription_required_now: false, safe_without_platform_subscription: true, backup_plan_documented: true,
      internal_use_ready: true, ready_for_real_tokens: true, external_access_ready: false,
      internal_blockers: [], platform_blockers: [],
      external_access_blockers: ["Internettoegang is uitgesteld. Gebruik eerst een domein, HTTPS en secure cookies voordat de site buiten het lokale netwerk bereikbaar wordt."],
      blockers: [], next_checks: ["Controleer het herstelbewijs."],
    });
    if (url.pathname === "/products") return reply(products);
    if (/^\/products\/\d+$/.test(url.pathname)) return reply(products.find((p) => p.id === Number(url.pathname.split("/").pop())));
    if (url.pathname.endsWith("/media") && mediaFails) return reply({ detail: "Test foto storing" }, 503);
    if (url.pathname === "/bambu/printers") {
      if (printerFails) return reply({ detail: "Geen testprinter bereikbaar" }, 503);
      return reply([
        { id: 1, name: "P2S actief", model: "P2S", host: "printer-1", mqtt_port: 8883, active: true, last_status: "bereikbaar", last_seen_at: "2026-09-13T08:00:00Z", printer_state: "RUNNING", print_progress: 75, nozzle_temperature: 220, bed_temperature: null, current_task: "Telefoonhouder" },
        { id: 2, name: "P2S gereed", model: "P2S", host: "printer-2", mqtt_port: 8883, active: true, last_status: "bereikbaar", last_seen_at: "2026-09-13T07:00:00Z", printer_state: "FINISH", print_progress: 100, nozzle_temperature: null, bed_temperature: null, current_task: "Dumpling" },
      ]);
    }
    return reply([]);
  });
  process.env.API_BASE_URL = await listen(fixture);
  process.env.BACKEND_INTERNAL_TOKEN = "local-browser-fixture-only";
  process.env.AUTH_ENABLED = "false";
  const app = require("next")({ dev: false, hostname: "127.0.0.1" });
  let server, browser;
  try {
    await app.prepare();
    server = http.createServer(app.getRequestHandler());
    const base = await listen(server);
    browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const screenshots = path.join(process.cwd(), ".next", "audit-screenshots");
    fs.mkdirSync(screenshots, { recursive: true });
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      await page.goto(`${base}/catalogus`);
      await page.getByRole("link", { name: "Telefoonhouder", exact: true }).waitFor();
      assert.equal(await page.getByRole("link", { name: "Archiefproduct", exact: true }).count(), 0);
      assert.ok(await page.getByText("Printeradvies kon niet worden geladen", { exact: true }).isVisible());
      await page.getByRole("link", { name: "Archief", exact: true }).click();
      await page.getByRole("link", { name: "Archiefproduct", exact: true }).waitFor();
      assert.equal(await page.getByRole("link", { name: "Telefoonhouder", exact: true }).count(), 0);
      await page.goto(`${base}/catalogus/nieuw`);
      await page.getByLabel("Productnaam", { exact: true }).waitFor();
      assert.equal(await page.locator('form').filter({ has: page.getByLabel("Productnaam", { exact: true }) }).locator('input:not([type="file"]):not([type="checkbox"]):visible').count(), 1);
      assert.equal(await page.getByLabel("Producttitel", { exact: true }).isVisible(), false);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.screenshot({ path: path.join(screenshots, `new-product-${viewport.width}.png`), fullPage: true });
    }
    await page.getByLabel("Productnaam", { exact: true }).fill("Nieuw testproduct");
    await page.getByLabel("Productbestand (optioneel)").setInputFiles({ name: "model.stl", mimeType: "application/octet-stream", buffer: Buffer.from("test model") });
    await page.getByRole("button", { name: "Product aanmaken", exact: true }).click();
    await page.getByRole("button", { name: "Bestand opnieuw uploaden", exact: true }).waitFor();
    await page.getByRole("button", { name: "Bestand opnieuw uploaden", exact: true }).click();
    await page.waitForURL(/\/catalogus\/3\?tab=printbestand/);
    assert.equal(creates, 1);
    assert.equal(uploads, 2);
    mediaFails = true;
    await page.goto(`${base}/catalogus/1?tab=fotos`);
    await page.getByText("Foto's konden niet worden geladen", { exact: true }).waitFor();
    assert.equal(await page.locator('input[type="file"]').count(), 0);
    mediaFails = false;
    await page.getByRole("link", { name: "Opnieuw proberen", exact: true }).first().click();
    await page.locator('input[type="file"]').waitFor({ state: "attached" });
    assert.equal(await page.getByText("Foto's konden niet worden geladen", { exact: true }).count(), 0);
    await page.getByRole("link", { name: "Printbestand", exact: true }).click();
    await page.getByRole("button", { name: "Open in Bambu Studio", exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Open in Bambu Studio", exact: true }).isEnabled(), true);
    await page.goto(`${base}/filament`);
    await page.getByText("Bambu Lab - PLA - Rood", { exact: true }).waitFor();
    assert.equal(await page.locator("#filament-toevoegen").getByLabel("Merk", { exact: true }).isVisible(), false);
    await page.getByText("Nieuwe filamentrol toevoegen", { exact: true }).click();
    assert.equal(await page.locator("#filament-toevoegen").getByLabel("Merk", { exact: true }).isVisible(), true);
    await page.goto(`${base}/verkoopkanalen`);
    await page.getByRole("heading", { name: "Koppelingsstatus", exact: true }).waitFor();
    assert.equal(await page.getByText("Nieuw verkoopkanaal toevoegen", { exact: true }).isVisible(), false);
    await page.getByText("Verkoopkanalen toevoegen of wijzigen", { exact: true }).click();
    assert.equal(await page.getByText("Nieuw verkoopkanaal toevoegen", { exact: true }).isVisible(), true);
    await page.goto(`${base}/orders?status=nieuw`);
    await page.getByRole("link", { name: "WEB-TEST-1", exact: true }).waitFor();
    assert.equal(await page.getByLabel("Maximaal aantal orders", { exact: true }).isVisible(), false);
    await page.getByText("Geavanceerde importinstellingen", { exact: true }).click();
    assert.equal(await page.getByLabel("Maximaal aantal orders", { exact: true }).isVisible(), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(screenshots, "daily-work-mobile.png"), fullPage: true });
    await page.getByRole("link", { name: "WEB-TEST-1", exact: true }).click();
    await page.waitForURL(/\/orders\/1\?returnTo=/);
    await page.getByRole("link", { name: "Terug naar orders", exact: true }).click();
    await page.waitForURL(`${base}/orders?status=nieuw`);
    await page.getByRole("link", { name: "WEB-TEST-1", exact: true }).click();
    await page.getByRole("button", { name: "Order verwerken", exact: true }).click();
    await page.getByText("Order verwerkt: voorraad en printplanning zijn bijgewerkt. Verkoopboeking is vastgelegd.", { exact: true }).waitFor();
    assert.equal(orderProcesses, 1);
    await page.reload();
    await page.getByRole("link", { name: "Open deze taak in Productie", exact: true }).click();
    await page.waitForURL((url) => url.pathname === "/printplanning" && url.searchParams.get("job") === "1" && url.hash === "#printtaak-1");
    assert.equal(await page.locator("#printtaak-1").evaluate((element) => element.open), true);
    await page.getByLabel("Gelukt", { exact: true }).fill("1");
    await page.getByLabel("Mislukt", { exact: true }).fill("1");
    await page.getByLabel("Naar order", { exact: true }).fill("1");
    await page.getByRole("button", { name: "Resultaat verwerken", exact: true }).click();
    await page.getByText("Printresultaat verwerkt. Extra gelukte prints zijn naar vrije voorraad geboekt.", { exact: true }).waitFor();
    assert.deepEqual(completedPayload, { quantity_succeeded: 1, quantity_failed: 1, quantity_to_order: 1 });
    printerFails = false;
    await page.goto(`${base}/bambu-printers`);
    await page.getByText("Resterende tijd onbekend", { exact: true }).waitFor();
    assert.ok(await page.getByText("Geen actieve print", { exact: true }).isVisible());
    assert.ok(await page.getByText("Laatste bekende opdracht: Dumpling", { exact: true }).isVisible());
    assert.equal(await page.getByText("Niet geregistreerd", { exact: true }).count(), 2);
    assert.ok(await page.getByText("220°C", { exact: true }).isVisible());
    assert.ok(await page.getByText("Onbekend", { exact: true }).count() >= 4);
    assert.equal(await page.getByText(/min resterend/).count(), 0);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(screenshots, "printer-measurements-mobile.png"), fullPage: true });
    await page.goto(`${base}/analyse`);
    await page.getByText("Berekend over 30 dagen op basis van gemiddelde weekverkoop en vrije voorraad.", { exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Printtaak maken", exact: true }).count(), 0);
    await page.getByRole("button", { name: "Accepteren", exact: true }).click();
    await page.getByRole("button", { name: "Printtaak maken", exact: true }).waitFor();
    await page.getByRole("button", { name: "Aanpassen", exact: true }).click();
    assert.ok(await page.getByLabel("Veiligheidsvoorraad", { exact: true }).isVisible());
    assert.ok(await page.getByText("Bezettingsanalyse nog niet beschikbaar", { exact: true }).isVisible());
    assert.ok(await page.getByText("Verbruiksanalyse nog niet beschikbaar", { exact: true }).isVisible());
    await page.getByText("Toon 1 afgehandelde adviezen", { exact: true }).click();
    assert.ok(await page.getByText("Eerder omgezet naar een printtaak.", { exact: true }).isVisible());
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(screenshots, "stock-advice-mobile.png"), fullPage: true });
    await page.goto(`${base}/instellingen`);
    await page.getByRole("heading", { name: "1. Intern gebruiken", exact: true }).waitFor();
    assert.ok(await page.getByRole("heading", { name: "2. Echte platformtokens", exact: true }).isVisible());
    assert.ok(await page.getByRole("heading", { name: "3. Toegang via internet", exact: true }).isVisible());
    assert.ok(await page.getByText("Opslag klaar", { exact: true }).isVisible());
    assert.ok(await page.getByText("Uitgesteld", { exact: true }).first().isVisible());
    assert.ok(await page.getByText(/Laatste bewijs: 13 sep 2026.*Maximaal 48 uur oud/).first().isVisible());
    assert.equal(await page.getByText("HTTPS/secure cookies zijn nog niet actief. Gebruik daarom nog geen externe toegang.", { exact: true }).count(), 0);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: path.join(screenshots, "readiness-mobile.png"), fullPage: true });
    assert.ok(overviewRequests.some((query) => query.includes("page=1") && query.includes("page_size=20") && query.includes("view=actief")));
    assert.ok(overviewRequests.some((query) => query.includes("view=archief")));
    assert.deepEqual(errors, []);
    console.log("Browser checks passed: core workflow, daily-work hierarchy, truthful measurements, stock advice and separated live-readiness decisions.");
    console.log(`Screenshots: ${screenshots}`);
  } finally {
    await browser?.close();
    if (server) { server.closeAllConnections(); await new Promise((resolve) => server.close(resolve)); }
    await app.close();
    fixture.closeAllConnections();
    await new Promise((resolve) => fixture.close(resolve));
  }
}
main().then(() => process.exit(0), (error) => { console.error(error); process.exit(1); });
