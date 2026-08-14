import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = getBackendBaseUrl();

type BackendUser = {
  id: number;
  email: string;
  display_name?: string | null;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  must_change_password?: boolean;
  mfa_enabled: boolean;
  last_login_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export async function GET(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const response = await backendFetch(`${API_BASE_URL}/auth/users`, {
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  if (!response.ok || !Array.isArray(data)) {
    return NextResponse.json({ detail: data.detail || "Accountstatus ophalen mislukt." }, { status: response.status || 502 });
  }

  const user = (data as BackendUser[]).find((item) => item.email.toLowerCase() === session.email.toLowerCase());
  if (!user) {
    return NextResponse.json({ detail: "Ingelogde gebruiker is niet gevonden in de backend." }, { status: 404 });
  }

  return NextResponse.json({
    id: user.id,
    email: user.email,
    display_name: user.display_name,
    role: user.role,
    is_active: user.is_active,
    must_change_password: Boolean(user.must_change_password || session.mustChangePassword),
    mfa_enabled: user.mfa_enabled,
    last_login_at: user.last_login_at,
    created_at: user.created_at,
    updated_at: user.updated_at,
    session_expires_at: new Date(session.exp * 1000).toISOString(),
  });
}
