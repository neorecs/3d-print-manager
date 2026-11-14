import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await backendFetch(`${API_BASE_URL}/product-publications/${encodeURIComponent(id)}/listing-package/photos.zip`, { cache: "no-store" });
  if (!response.ok) return new Response("Foto's niet beschikbaar", { status: response.status });
  return new Response(response.body, {
    status: 200,
    headers: {
      "content-type": "application/zip",
      "content-disposition": response.headers.get("content-disposition") || 'attachment; filename="fotos.zip"',
      "cache-control": "private, no-store",
    },
  });
}
