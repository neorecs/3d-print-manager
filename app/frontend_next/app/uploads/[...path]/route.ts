import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const safePath = path.map((part) => encodeURIComponent(part)).join("/");
  const response = await fetch(`${API_BASE_URL}/uploads/${safePath}`, { cache: "no-store" });

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
