import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest, setSessionCookie } from "@/lib/auth";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function POST(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const payload = await request.json().catch(() => ({}));
  const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: session.email,
      current_password: payload.currentPassword,
      new_password: payload.newPassword,
    }),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  if (!response.ok) {
    return NextResponse.json(data, { status: response.status });
  }

  const user = data.user || {};
  const nextResponse = NextResponse.json({ user, must_change_password: false });
  return setSessionCookie(nextResponse, user.email || session.email, user.display_name || session.name, user.role || session.role, false);
}
