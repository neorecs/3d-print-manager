import { NextRequest } from "next/server";

import { verifyBambuStudioFileToken } from "@/lib/bambuStudioLaunch";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export const dynamic = "force-dynamic";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ token: string; filename: string }> }) {
  const { token, filename } = await params;
  if (!filename.toLowerCase().endsWith(".gcode.3mf")) {
    return Response.json({ detail: "Alleen printklare .gcode.3mf bestanden zijn toegestaan" }, { status: 400 });
  }

  const verified = await verifyBambuStudioFileToken(token, filename);
  if (!verified) {
    return Response.json({ detail: "Deze Bambu Studio-link is ongeldig of verlopen" }, { status: 403 });
  }

  const response = await fetch(`${API_BASE_URL}/products/${verified.productId}/print-file/download`, { cache: "no-store" });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    return Response.json(data || { detail: "Printbestand kon niet worden opgehaald" }, { status: response.status });
  }

  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/octet-stream",
      "content-disposition": `attachment; filename="${filename}"`,
      "content-length": response.headers.get("content-length") || "",
      "cache-control": "private, no-store",
      "x-content-type-options": "nosniff",
    },
  });
}
