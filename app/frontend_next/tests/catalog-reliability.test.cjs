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
  vm.runInNewContext(code, { module, exports: module.exports, URLSearchParams, Error, require: (name) => {
    if (name in imports) return imports[name];
    throw new Error(`Unexpected import ${name}`);
  } });
  return module.exports;
}
const results = load("lib/loadResult.ts");
const catalog = load("lib/catalogView.ts");
function api(failures = []) {
  return load("lib/api.ts", {
    "./format": {}, "./loadResult": results,
    "./backend-auth": { getBackendBaseUrl: () => "http://test", backendFetch: async (url) => {
      const endpoint = new URL(url).pathname;
      if (failures.includes(endpoint)) return Response.json({ detail: "test failure" }, { status: 503 });
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
    ["getOrdersData", "/order-items"], ["getOrderDetailData", "/accounting/sales"],
    ["getSalesChannelsData", "/sales-markets"], ["getAIProductStatus", "/ai/product-draft/status"],
    ["getSystemReadiness", "/system/readiness"], ["getProductCatalogData", "/inventory/products"],
  ]) await assert.rejects(api([endpoint])[method](1), /503/);
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
