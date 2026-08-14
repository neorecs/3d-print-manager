import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await backendFetch(`${API_BASE_URL}/product-publications/${id}/check`, {
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
