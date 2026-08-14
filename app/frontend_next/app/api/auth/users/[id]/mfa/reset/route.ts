import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";
import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSessionFromRequest(request);
  if (session?.role !== "admin") {
    return NextResponse.json({ detail: "Alleen admins mogen gebruikers beheren." }, { status: 403 });
  }

  const { id } = await params;
  const response = await backendFetch(`${API_BASE_URL}/auth/users/${id}/mfa/reset`, {
    method: "POST",
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
