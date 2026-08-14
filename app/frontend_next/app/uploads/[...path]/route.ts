import { NextRequest } from "next/server";
import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

export async function GET(_request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const safePath = path.map((part) => encodeURIComponent(part)).join("/");
  const response = await backendFetch(`${API_BASE_URL}/secure-files/${safePath}`, { cache: "no-store" });

  if (!response.ok) {
    return new Response("Bestand niet gevonden", { status: response.status });
  }

  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/octet-stream",
      "content-length": response.headers.get("content-length") || "",
      "cache-control": "private, no-store",
    },
  });
}
