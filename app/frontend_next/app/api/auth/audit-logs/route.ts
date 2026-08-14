import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";
import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = getBackendBaseUrl();

export async function GET(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (session?.role !== "admin") {
    return NextResponse.json({ detail: "Alleen admins mogen auditlogs bekijken." }, { status: 403 });
  }

  const limit = request.nextUrl.searchParams.get("limit") || "100";
  const response = await backendFetch(`${API_BASE_URL}/auth/audit-logs?limit=${encodeURIComponent(limit)}`, {
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
