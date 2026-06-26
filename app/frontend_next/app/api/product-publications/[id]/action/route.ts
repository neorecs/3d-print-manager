import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";
const allowedActions = new Set(["publish", "sync", "pause"]);

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const payload = await request.json().catch(() => ({}));
  const action = String(payload.action || "");

  if (!allowedActions.has(action)) {
    return NextResponse.json({ detail: "Onbekende publicatieactie" }, { status: 400 });
  }

  const response = await fetch(`${API_BASE_URL}/product-publications/${id}/${action}`, {
    method: "POST",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
