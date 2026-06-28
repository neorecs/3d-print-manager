import { NextResponse } from "next/server";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function POST(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/orders/import/etsy${query ? `?${query}` : ""}`, { method: "POST" });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
