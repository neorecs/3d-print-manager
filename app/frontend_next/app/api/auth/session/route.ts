import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME, authIsEnabled, getSessionFromCookieStore } from "@/lib/auth";

export async function GET() {
  const cookieStore = await cookies();
  const session = await getSessionFromCookieStore(cookieStore.get(AUTH_COOKIE_NAME)?.value);

  return NextResponse.json({
    authEnabled: authIsEnabled(),
    authenticated: Boolean(session),
    user: session ? { email: session.email, name: session.name, role: session.role } : null,
  });
}
