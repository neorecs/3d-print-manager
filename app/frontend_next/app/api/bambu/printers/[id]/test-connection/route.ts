import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await fetch(`${API_BASE_URL}/bambu/printers/${id}/test-connection`, {
    method: "POST",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
