const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

// Run the actual TypeScript handlers with an isolated backend; no printer or network calls.
function load(file, imports = {}, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, "..", file), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, {
    module, exports: module.exports,
    require: (name) => { if (name in imports) return imports[name]; throw new Error(`Unexpected import: ${name}`); },
    URL, Response, AbortSignal, TextEncoder, Uint8Array, btoa, crypto: require("node:crypto").webcrypto,
    process: { env: { AUTH_SECRET: "isolated-test-key-not-a-production-secret" } },
    ...globals,
  }, { filename: file });
  return module.exports;
}
const launch = load("lib/bambuStudioLaunch.ts");
const client = load("lib/bambuStudioClient.ts");
const routePath = "app/api/products/[id]/print-file/open-in-bambu-studio/route.ts";
function handler(fetcher) {
  return load(routePath, {
    "@/lib/backend-auth": { backendFetch: fetcher, getBackendBaseUrl: () => "http://backend" },
    "next/server": { NextResponse: { json: Response.json.bind(Response) } },
    "@/lib/bambuStudioLaunch": launch,
  }).POST;
}
function request(payload = {}) {
  return { url: "http://manager/api/products/1/print-file/open-in-bambu-studio", headers: new Headers(), json: async () => payload };
}

test("every supported file creates a signed source handoff and records its job without a printer", async () => {
  for (const suffix of launch.BAMBU_STUDIO_FILE_SUFFIXES) {
    let recorded = 0;
    const post = handler(async (url, options) => {
      const pathname = new URL(url).pathname;
      if (pathname === "/products/1") return Response.json({ name: "Model", print_file_path: `prints/model${suffix}` });
      if (pathname === "/bambu/printers") return Response.json([]);
      if (pathname === "/print-jobs/8/bambu-studio-opened") {
        assert.deepEqual(JSON.parse(options.body), { printer_id: null, product_id: 1, product_variant_id: 2 });
        recorded++;
        return Response.json({});
      }
      throw new Error(`Unexpected call: ${pathname}`);
    });
    const response = await post(request({ variant_id: 2, print_job_id: 8 }), { params: Promise.resolve({ id: "1" }) });
    assert.equal(response.status, 200, suffix);
    const data = await response.json();
    const url = new URL(data.file_url);
    const parts = url.pathname.split("/");
    assert.equal(url.searchParams.get("mode"), "source");
    assert.ok(await launch.verifyBambuStudioFileToken(parts.at(-2), parts.at(-1), "source"));
    assert.equal(recorded, 1, suffix);
  }
});

test("printer errors, missing variants, incompatible settings and planning errors do not block Studio", async () => {
  for (const scenario of ["offline", "incompatible", "planning-error", "no-variant"]) {
    const post = handler(async (url) => {
      const pathname = new URL(url).pathname;
      if (pathname === "/products/1") return Response.json({ name: "Model", print_file_path: "model.gcode.3mf" });
      if (pathname === "/bambu/printers") {
        if (scenario === "offline") throw new Error("offline");
        return Response.json([{ id: 3, active: true }]);
      }
      if (pathname.endsWith("/preparation")) return Response.json({ detail: "Slice opnieuw voor dit materiaal." }, { status: 409 });
      if (pathname.endsWith("/bambu-studio-opened")) return Response.json({}, { status: 503 });
      throw new Error(`Unexpected call: ${pathname}`);
    });
    const response = await post(request(scenario === "no-variant" ? {} : { variant_id: 2, print_job_id: 8 }), { params: Promise.resolve({ id: "1" }) });
    assert.equal(response.status, 200, scenario);
    const data = await response.json();
    assert.match(data.launcher_url, /^printmanager:\/\/open/);
    if (scenario !== "no-variant") assert.ok(data.warnings.length);
  }
});

test("source download remains signed and streams original bytes, including sliced files", async () => {
  const filename = "model.gcode.3mf";
  const token = await launch.createBambuStudioFileToken(1, filename, "source");
  let calls = 0;
  const get = load("app/api/bambu-studio/files/[token]/[filename]/route.ts", {
    "@/lib/backend-auth": { getBackendBaseUrl: () => "http://backend", backendFetch: async (url) => {
      assert.equal(new URL(url).pathname, "/products/1/print-file/source-download");
      calls++;
      return new Response(new Uint8Array([0, 1, 2, 255]));
    } },
    "next/server": {}, "@/lib/bambuStudioLaunch": launch,
  }).GET;
  const params = Promise.resolve({ token, filename });
  const response = await get({ nextUrl: new URL("http://manager/file?mode=source") }, { params });
  assert.equal(response.status, 200);
  assert.deepEqual([...new Uint8Array(await response.arrayBuffer())], [0, 1, 2, 255]);
  assert.equal((await get({ nextUrl: new URL("http://manager/file") }, { params })).status, 403);
  assert.equal((await get({ nextUrl: new URL("http://manager/file?mode=source") }, { params: Promise.resolve({ token, filename: "other.stl" }) })).status, 403);
  assert.equal(calls, 1);
});

test("available matching AMS advice selects the nearest color and includes its observation time", async () => {
  const post = handler(async (url) => {
    const parsed = new URL(url);
    if (parsed.pathname === "/products/1") return Response.json({ name: "Model", print_file_path: "model.gcode.3mf" });
    if (parsed.pathname === "/bambu/printers") return Response.json([
      { id: 3, active: true, last_seen_at: "2026-09-11T10:00:00Z" },
      { id: 4, active: true, last_seen_at: "2026-09-11T11:00:00Z" },
    ]);
    if (parsed.pathname.endsWith("/preparation")) {
      const id = Number(parsed.searchParams.get("printer_id"));
      return Response.json({ printer_id: id, printer_name: `Printer ${id}`, color_distance: id === 4 ? 0 : 20, recommended_slot: { ams_id: 0, tray_id: 1, label: "AMS 1" } });
    }
    throw new Error(`Unexpected call: ${url}`);
  });
  const response = await post(request({ variant_id: 2, printer_id: 3 }), { params: Promise.resolve({ id: "1" }) });
  const data = await response.json();
  assert.equal(data.preparation.printer_id, 4);
  assert.equal(data.preparation.last_seen_at, "2026-09-11T11:00:00Z");
  assert.match(client.studioHandoffMessage(data), /Laatste printermeting/);
});

test("shared client requests only the handoff, never live printer refresh or start", async () => {
  let calls = 0;
  const shared = load("lib/bambuStudioClient.ts", {}, { fetch: async (url, options) => {
    assert.equal(url, "/api/products/1/print-file/open-in-bambu-studio");
    assert.equal(JSON.parse(options.body).print_job_id, 8);
    calls++;
    return Response.json({ launcher_url: "printmanager://open?file=test" });
  } });
  assert.match((await shared.requestStudioHandoff(1, 2, undefined, 8)).launcher_url, /^printmanager:/);
  assert.equal(calls, 1);
});

test("readable names, unknown AMS values and truthful handoff messages", () => {
  assert.equal(client.readablePrintFilename("prints/0123456789abcdef0123456789abcdef-my-model.3mf"), "my-model.3mf");
  assert.equal(client.readablePrintFilename("prints/my-model.3mf"), "my-model.3mf");
  for (const value of [-1, 101, NaN, Infinity, null, undefined]) assert.equal(client.amsRemainingLabel(value), "restvoorraad onbekend");
  assert.equal(client.amsRemainingLabel(0), "0%");
  assert.equal(client.amsRemainingLabel(100), "100%");
  assert.match(client.studioHandoffMessage({ launcher_url: "test" }), /aangeboden/);
});
