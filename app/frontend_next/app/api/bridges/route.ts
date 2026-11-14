import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

export async function GET() {
  const response = await backendFetch(`${API_BASE_URL}/bridges`, { cache: "no-store" });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}

export async function POST(request: Request) {
  const payload = await request.json().catch(() => ({}));
  const response = await backendFetch(`${API_BASE_URL}/bridges`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
