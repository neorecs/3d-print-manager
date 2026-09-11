const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(file, imports, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, "..", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, Error, ...globals, require: (name) => {
    if (name in imports) return imports[name];
    throw new Error(`Unexpected import ${name}`);
  } });
  return module.exports;
}

test("order action proxy sends processing to one atomic backend endpoint", async () => {
  let calls = 0;
  const route = load("app/api/orders/[id]/action/route.ts", {
    "next/server": { NextResponse: { json: Response.json.bind(Response) } },
    "@/lib/backend-auth": { getBackendBaseUrl: () => "http://backend", backendFetch: async (url, options) => {
      assert.equal(url, "http://backend/orders/12/process");
      assert.equal(options.method, "POST");
      calls++;
      return Response.json({ status: "processed" });
    } },
  });
  const response = await route.POST({ json: async () => ({ action: "process" }) }, { params: Promise.resolve({ id: "12" }) });
  assert.equal(response.status, 200);
  assert.equal(calls, 1);
});

test("primary button issues one request and does not separately book accounting", async () => {
  const calls = [];
  let refreshes = 0;
  const { OrderActions } = load("app/orders/OrderActions.tsx", {
    "react/jsx-runtime": require("react/jsx-runtime"),
    "react": { useState: (initial) => [initial, () => {}] },
    "next/navigation": { useRouter: () => ({ refresh: () => { refreshes++; } }) },
  }, { fetch: async (url, options) => {
    calls.push([url, JSON.parse(options.body).action]);
    return Response.json({ message: "Order verwerkt" });
  } });
  const tree = OrderActions({ orderId: 12 });
  const button = tree.props.children.find((child) => child?.type === "button");
  await button.props.onClick();
  assert.deepEqual(calls, [["/api/orders/12/action", "process"]]);
  assert.equal(refreshes, 1);
});
