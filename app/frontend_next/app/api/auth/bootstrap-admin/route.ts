import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const response = await backendFetch(`${API_BASE_URL}/auth/bootstrap-admin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bootstrap_secret: payload.bootstrapSecret,
      email: payload.email,
      password: payload.password,
      display_name: payload.displayName || "Beheerder",
    }),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  return NextResponse.json(data, { status: response.status });
}
