import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({ period_days: 30, safety_stock: 2, weeks_ahead: 1 }));
  const response = await backendFetch(`${API_BASE_URL}/stock-recommendations/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
