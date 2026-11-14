import { backendFetch, getBackendBaseUrl } from "@/lib/backend";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

// Called by the Bambu bridge agent; it authenticates with its own bridge token.
export async function POST(request: Request) {
  const headers = new Headers({ "Content-Type": "application/json" });
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);
  const response = await backendFetch(`${API_BASE_URL}/bridge-agent/sync`, { method: "POST", headers, body: await request.text() });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
