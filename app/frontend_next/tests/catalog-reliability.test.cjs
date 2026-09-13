const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(file, imports = {}) {
  const source = fs.readFileSync(path.join(__dirname, "..", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, URL, URLSearchParams, Error, require: (name) => {
    if (name in imports) return imports[name];
    throw new Error(`Unexpected import ${name}`);
  } });
  return module.exports;
}
const results = load("lib/loadResult.ts");
const catalog = load("lib/catalogView.ts");
const navigation = load("lib/navigation.ts");
const printerPresentation = load("lib/printerPresentation.ts", { "./types": {} });
function api(failures = []) {
  return load("lib/api.ts", {
    "./format": {}, "./loadResult": results,
    "./backend-auth": { getBackendBaseUrl: () => "http://test", backendFetch: async (url) => {
      const endpoint = new URL(url).pathname;
      if (failures.includes(endpoint)) return Response.json({ detail: "test failure" }, { status: 503 });
      if (endpoint === "/products/overview") return Response.json({ rows: [], metrics: { products: 0, variants: 0, low_stock: 0, published: 0, margin_potential: 0 }, page: 1, page_size: 20, page_count: 1, total: 0, view: "actief" });
      if (endpoint === "/orders/overview") return Response.json({ orders: [], order_items: [], platforms: [], print_jobs: [], import_logs: [], metrics: { total: 0, new: 0, paid: 0, production: 0, packed: 0, shipped: 0, cancelled: 0, revenue: 0 }, page: 1, page_size: 25, page_count: 1, total: 0, status: "alle" });
      if (endpoint === "/dashboard/overview") return Response.json({ metrics: {}, monthly_revenue: [], printers: [], top_products: [], low_inventory: [], open_print_jobs: [] });
      if (endpoint === "/search") return Response.json({ products: [], orders: [], printers: [] });
      return Response.json(endpoint === "/products/1" ? { id: 1, name: "Product" } : []);
    } },
  });
}

test("successful empty data and unavailable data remain distinguishable", async () => {
  const empty = await results.loadResult(Promise.resolve([]));
  const failed = await results.loadResult(Promise.reject(new Error("offline")));
  assert.equal(empty.error, null);
  assert.equal(empty.data.length, 0);
  assert.equal(failed.data, null);
  assert.equal(failed.error, "offline");
});

test("product detail keeps unaffected sections and labels each failed optional section", async () => {
  const endpoints = { media: "/products/1/media", tags: "/products/1/tags", translations: "/products/1/translations", publications: "/products/1/publications", printers: "/bambu/printers" };
  for (const [key, endpoint] of Object.entries(endpoints)) {
    const data = await api([endpoint]).getProductDetailData(1);
    assert.equal(data.product.id, 1);
    assert.match(data.loadErrors[key], /503/);
    assert.equal(Object.keys(data.loadErrors).length, 1);
  }
  assert.equal(Object.keys((await api().getProductDetailData(1)).loadErrors).length, 0);
});

test("printer advice failure does not prevent catalog and planning from loading", async () => {
  for (const method of ["getProductCatalogData", "getPrintPlanningData"]) {
    const data = await api(["/bambu/printers"])[method]();
    assert.match(data.printerLoadError, /503/);
    assert.equal(data.printers.length, 0);
  }
});

test("critical failures never become empty orders, sales channels or false system states", async () => {
  for (const [method, endpoint] of [
    ["getOrdersData", "/orders/overview"], ["getOrderDetailData", "/accounting/sales"],
    ["getSalesChannelsData", "/sales-markets"], ["getAIProductStatus", "/ai/product-draft/status"],
    ["getSystemReadiness", "/system/readiness"], ["getProductCatalogData", "/products/overview"],
    ["getDashboardData", "/dashboard/overview"],
  ]) await assert.rejects(api([endpoint])[method](1), /503/);
});

test("large overview screens send pagination and filters to bounded backend endpoints", async () => {
  const urls = [];
  const client = load("lib/api.ts", {
    "./format": {}, "./loadResult": results,
    "./backend-auth": { getBackendBaseUrl: () => "http://test", backendFetch: async (url) => {
      urls.push(String(url));
      const endpoint = new URL(url).pathname;
      if (endpoint === "/products/overview") return Response.json({ rows: [], metrics: {}, page: 3, page_size: 20, page_count: 5, total: 100, view: "archief" });
      if (endpoint === "/orders/overview") return Response.json({ orders: [], order_items: [], platforms: [], print_jobs: [], import_logs: [], metrics: {}, page: 4, page_size: 25, page_count: 8, total: 200, status: "nieuw" });
      if (endpoint === "/search") return Response.json({ products: [], orders: [], printers: [] });
      return Response.json([]);
    } },
  });
  await client.getProductCatalogData(3, "archief");
  await client.getOrdersData(4, "nieuw");
  await client.getSearchData("rode vaas");
  await client.getProductDetailData(1);
  assert.ok(urls.some((url) => url.includes("/products/overview?page=3&page_size=20&view=archief")));
  assert.ok(urls.some((url) => url.includes("/orders/overview?page=4&page_size=25&status=nieuw")));
  assert.ok(urls.some((url) => url.includes("/search?q=rode%20vaas&limit=20")));
  assert.ok(urls.some((url) => url.includes("/product-variants?product_id=1")));
  assert.ok(urls.some((url) => url.includes("/inventory/products?product_id=1")));
});

test("catalog selection excludes archived flags and statuses and does not lose rows", () => {
  const rows = [
    { product: { id: 1, active: true, status: "concept" } },
    { product: { id: 2, active: false, status: "concept" } },
    { product: { id: 3, active: true, status: "gearchiveerd" } },
  ];
  assert.equal(catalog.catalogRows(rows, "actief").length, 1);
  assert.equal(catalog.catalogRows(rows, "archief").length, 2);
  assert.equal(catalog.catalogRows(rows, "alle").length, 3);
});

test("manually selected ready status never overrides missing sale data", () => {
  const row = { product: { name: "Product", status: "klaar_voor_publicatie" }, variants: [{ active: true, sku: "SKU", default_sale_price: null }] };
  const missing = catalog.salesBasicsMissing(row);
  assert.ok(missing.includes("omschrijving"));
  assert.ok(missing.includes("SKU of prijs"));
  assert.ok(missing.includes("materiaal of kleur"));
});

test("product detail does not advertise an unimplemented history timeline", () => {
  const source = fs.readFileSync(path.join(__dirname, "..", "app", "catalogus", "[id]", "page.tsx"), "utf8");
  assert.doesNotMatch(source, /\["historie",\s*"Historie"\]/);
  assert.doesNotMatch(source, /producttijdlijn/);
});

test("navigation keeps list filters and focuses related work", () => {
  const list = navigation.ordersListHref("nieuw", 3);
  assert.equal(list, "/orders?status=nieuw&page=3");
  assert.equal(navigation.orderDetailHref(42, list), "/orders/42?returnTo=%2Forders%3Fstatus%3Dnieuw%26page%3D3");
  assert.equal(navigation.safeOrdersReturnHref("/orders?status=nieuw&page=3"), list);
  assert.equal(navigation.safeOrdersReturnHref("https://example.com/orders"), "/orders");
  assert.equal(navigation.printJobHref(7), "/printplanning?job=7#printtaak-7");
  assert.equal(navigation.productInventoryHref(9), "/catalogus/9?tab=voorraad");
});

test("printer presentation never invents measurements or remaining time", () => {
  const unknown = { id: 1, name: "P2S", host: "printer", mqtt_port: 8883, active: true };
  assert.equal(printerPresentation.operationalState(unknown), "onbekend");
  assert.equal(printerPresentation.progressLabel(unknown), "Voortgang onbekend");
  assert.equal(printerPresentation.temperatureLabel(null), "Onbekend");
  assert.equal(printerPresentation.remainingTimeLabel(unknown), "Geen actuele tijdmeting");
  assert.equal(printerPresentation.hasStatusMeasurement(unknown), false);

  const printing = { ...unknown, printer_state: "RUNNING", print_progress: 75, nozzle_temperature: 220, last_seen_at: "2026-09-13T08:00:00Z" };
  assert.equal(printerPresentation.progressLabel(printing), "75%");
  assert.equal(printerPresentation.temperatureLabel(printing.nozzle_temperature), "220°C");
  assert.equal(printerPresentation.remainingTimeLabel(printing), "Resterende tijd onbekend");
  assert.equal(printerPresentation.hasStatusMeasurement(printing), true);

  const finished = { ...printing, printer_state: "FINISH", current_task: "Dumpling" };
  assert.equal(printerPresentation.remainingTimeLabel(finished), "Geen actieve print");
  assert.equal(printerPresentation.taskLabel(finished), "Laatste bekende opdracht: Dumpling");
});
