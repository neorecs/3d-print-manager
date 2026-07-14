import { NextRequest, NextResponse } from "next/server";
import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

async function proxyJson(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}

export async function GET(request: NextRequest) {
  const forbidden = await requireAdmin(request);
  if (forbidden) return forbidden;
  return proxyJson("/auth/users");
}

export async function POST(request: NextRequest) {
  const forbidden = await requireAdmin(request);
  if (forbidden) return forbidden;
  const payload = await request.json().catch(() => ({}));
  return proxyJson("/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
async function requireAdmin(request: NextRequest) {
  const session = await getSessionFromRequest(request);
  if (session?.role !== "admin") {
    return NextResponse.json({ detail: "Alleen admins mogen gebruikers beheren." }, { status: 403 });
  }
  return null;
}
