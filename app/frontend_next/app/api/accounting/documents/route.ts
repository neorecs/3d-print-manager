import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

export async function GET() {
  const response = await backendFetch(`${API_BASE_URL}/accounting/documents`, { cache: "no-store" });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
