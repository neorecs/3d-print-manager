import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const payload = await request.json();
  const remaining = Number(payload.remaining_weight_grams);

  if (!Number.isFinite(remaining) || remaining < 0) {
    return NextResponse.json({ detail: "Resterend gewicht moet een positief getal zijn" }, { status: 400 });
  }

  const response = await backendFetch(`${API_BASE_URL}/filament/${id}/adjust?remaining_weight_grams=${encodeURIComponent(String(remaining))}`, {
    method: "POST",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
