import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest, setSessionCookie } from "@/lib/auth";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const payload = await request.json().catch(() => ({}));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  let response: Response;
  try {
    response = await backendFetch(`${API_BASE_URL}/auth/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: session.email,
        current_password: payload.currentPassword,
        new_password: payload.newPassword,
      }),
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    return NextResponse.json({ detail: "Backend reageert niet bij wachtwoord wijzigen. Probeer het opnieuw." }, { status: 504 });
  } finally {
    clearTimeout(timeout);
  }

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  if (!response.ok) {
    return NextResponse.json(data, { status: response.status });
  }

  const user = data.user || {};
  const nextResponse = NextResponse.json({ user, must_change_password: false });
  return setSessionCookie(
    nextResponse,
    user.email || session.email,
    user.display_name || session.name,
    user.role || session.role,
    false,
    Number(user.id || session.userId),
    Number(user.session_version || session.sessionVersion),
  );
}
