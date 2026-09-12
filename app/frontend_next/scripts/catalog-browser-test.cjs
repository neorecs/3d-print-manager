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
  let creates = 0, uploads = 0, mediaFails = false, orderProcesses = 0, completedPayload = null;
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
    if (url.pathname === "/orders/1") return reply({ ...orders[0], items: orderItems });
    if (url.pathname === "/products/overview") {
      overviewRequests.push(url.search);
      const view = url.searchParams.get("view") || "actief";
      const rows = products
        .filter((product) => view === "alle" || (view === "archief" ? !product.active || product.status === "gearchiveerd" : product.active && product.status !== "gearchiveerd"))
        .map((product) => ({ product, variants: variants.filter((item) => item.product_id === product.id), inventory: [], publications: [] }));
      return reply({ rows, metrics: { products: rows.length, variants: rows.flatMap((row) => row.variants).length, low_stock: 0, published: 0, margin_potential: 0 }, page: 1, page_size: 20, page_count: 1, total: rows.length, view });
    }
    if (url.pathname === "/orders") return reply(orders);
    if (url.pathname === "/order-items") return reply(orderItems);
    if (url.pathname === "/orders/import-logs") return reply([]);
    if (url.pathname === "/platforms") return reply([{ id: 1, name: "Testkanaal", type: "etsy", active: true }]);
    if (url.pathname === "/product-variants") return reply(variants);
    if (url.pathname === "/print-jobs") return reply(printJobs);
    if (url.pathname === "/print-batches") return reply([]);
    if (url.pathname === "/accounting/sales") return reply(accountingSales);
    if (url.pathname === "/products") return reply(products);
    if (/^\/products\/\d+$/.test(url.pathname)) return reply(products.find((p) => p.id === Number(url.pathname.split("/").pop())));
    if (url.pathname.endsWith("/media") && mediaFails) return reply({ detail: "Test foto storing" }, 503);
    if (url.pathname === "/bambu/printers") return reply({ detail: "Geen testprinter bereikbaar" }, 503);
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
    await page.goto(`${base}/orders/1`);
    await page.getByRole("button", { name: "Order verwerken", exact: true }).click();
    await page.getByText("Order verwerkt: voorraad en printplanning zijn bijgewerkt. Verkoopboeking is vastgelegd.", { exact: true }).waitFor();
    assert.equal(orderProcesses, 1);
    await page.goto(`${base}/printplanning`);
    await page.getByText("Printtaak #1", { exact: true }).click();
    await page.getByLabel("Gelukt", { exact: true }).fill("1");
    await page.getByLabel("Mislukt", { exact: true }).fill("1");
    await page.getByLabel("Naar order", { exact: true }).fill("1");
    await page.getByRole("button", { name: "Resultaat verwerken", exact: true }).click();
    await page.getByText("Printresultaat verwerkt. Extra gelukte prints zijn naar vrije voorraad geboekt.", { exact: true }).waitFor();
    assert.deepEqual(completedPayload, { quantity_succeeded: 1, quantity_failed: 1, quantity_to_order: 1 });
    assert.ok(overviewRequests.some((query) => query.includes("page=1") && query.includes("page_size=20") && query.includes("view=actief")));
    assert.ok(overviewRequests.some((query) => query.includes("view=archief")));
    assert.deepEqual(errors, []);
    console.log("Browser checks passed: product creation/recovery, Studio handoff, atomic order processing and print-result registration.");
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
