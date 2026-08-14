import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const payload = await request.json().catch(() => ({}));
  const response = await backendFetch(`${API_BASE_URL}/auth/mfa/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: session.email,
      password: payload.password,
      code: payload.code,
    }),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  return NextResponse.json(data, { status: response.status });
}
