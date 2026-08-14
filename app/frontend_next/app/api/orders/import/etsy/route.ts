import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.toString();
  const response = await backendFetch(`${API_BASE_URL}/orders/import/etsy${query ? `?${query}` : ""}`, { method: "POST" });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
