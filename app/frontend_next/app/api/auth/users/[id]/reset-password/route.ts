import { NextRequest, NextResponse } from "next/server";
import { getSessionFromRequest } from "@/lib/auth";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSessionFromRequest(request);
  if (session?.role !== "admin") {
    return NextResponse.json({ detail: "Alleen admins mogen gebruikers beheren." }, { status: 403 });
  }

  const { id } = await params;
  const payload = await request.json().catch(() => ({}));
  const response = await fetch(`${API_BASE_URL}/auth/users/${id}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
