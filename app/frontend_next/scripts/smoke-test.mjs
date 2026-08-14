const baseUrl = process.env.SMOKE_BASE_URL || "http://127.0.0.1:3000";

async function assertResponse(path, expectedStatus) {
  const response = await fetch(`${baseUrl}${path}`, { redirect: "manual" });
  if (response.status !== expectedStatus) {
    throw new Error(`${path} gaf HTTP ${response.status}; verwacht ${expectedStatus}.`);
  }
  return response;
}

await assertResponse("/login", 200);
const protectedPage = await assertResponse("/", 307);
if (!protectedPage.headers.get("location")?.includes("/login")) {
  throw new Error("De onbeveiligde dashboardaanvraag werd niet naar /login gestuurd.");
}

console.log("Frontend rooktest geslaagd: login bereikbaar en dashboard afgeschermd.");
