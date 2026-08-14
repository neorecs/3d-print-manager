import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const payload = await request.json();
  const response = await backendFetch(`${API_BASE_URL}/ai/product-draft/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
