import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const formData = await request.formData();
  const response = await backendFetch(`${API_BASE_URL}/bambu/printers/${id}/print-files/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
