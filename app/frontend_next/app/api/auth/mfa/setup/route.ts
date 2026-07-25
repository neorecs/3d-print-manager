import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function POST(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const payload = await request.json().catch(() => ({}));
  const response = await fetch(`${API_BASE_URL}/auth/mfa/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: session.email,
      password: payload.password,
    }),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  return NextResponse.json(data, { status: response.status });
}
