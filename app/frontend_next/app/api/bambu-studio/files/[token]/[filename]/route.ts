import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest } from "next/server";

import { bambuStudioFileSuffix, isSlicedBambuPrintFile, verifyBambuStudioFileToken } from "@/lib/bambuStudioLaunch";

const API_BASE_URL = getBackendBaseUrl();

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: { params: Promise<{ token: string; filename: string }> }) {
  const { token, filename } = await params;
  if (!bambuStudioFileSuffix(filename)) {
    return Response.json({ detail: "Dit bestandstype wordt niet ondersteund door Bambu Studio" }, { status: 400 });
  }

  const sliced = isSlicedBambuPrintFile(filename);
  const variantId = Number(request.nextUrl.searchParams.get("variant_id"));
  const printerId = Number(request.nextUrl.searchParams.get("printer_id"));
  const amsId = Number(request.nextUrl.searchParams.get("ams_id"));
  const trayId = Number(request.nextUrl.searchParams.get("tray_id"));
  if (sliced && ![variantId, printerId, amsId, trayId].every(Number.isInteger)) {
    return Response.json({ detail: "De Bambu Studio-link mist printer- of AMS-gegevens" }, { status: 400 });
  }
  const context = sliced ? `${variantId}:${printerId}:${amsId}:${trayId}` : "source";
  const verified = await verifyBambuStudioFileToken(token, filename, context);
  if (!verified) {
    return Response.json({ detail: "Deze Bambu Studio-link is ongeldig of verlopen" }, { status: 403 });
  }

  const fileUrl = sliced
    ? new URL(`${API_BASE_URL}/products/${verified.productId}/print-file/prepared-download`)
    : new URL(`${API_BASE_URL}/products/${verified.productId}/print-file/download`);
  if (sliced) {
    fileUrl.searchParams.set("variant_id", String(variantId));
    fileUrl.searchParams.set("printer_id", String(printerId));
    fileUrl.searchParams.set("ams_id", String(amsId));
    fileUrl.searchParams.set("tray_id", String(trayId));
  }
  const response = await backendFetch(fileUrl, { cache: "no-store" });
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
