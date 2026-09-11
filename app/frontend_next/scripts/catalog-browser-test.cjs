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
  let creates = 0, uploads = 0, mediaFails = false;
  const products = [
    { id: 1, name: "Telefoonhouder", active: true, status: "klaar_voor_publicatie", print_file_path: "model.stl" },
    { id: 2, name: "Archiefproduct", active: false, status: "gearchiveerd" },
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
    assert.deepEqual(errors, []);
    console.log("Browser checks passed: desktop/mobile, archive filter, compact form, upload retry without duplicate, failed media section, Studio remains available.");
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
