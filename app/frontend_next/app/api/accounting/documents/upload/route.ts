import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const response = await backendFetch(`${API_BASE_URL}/accounting/documents/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
