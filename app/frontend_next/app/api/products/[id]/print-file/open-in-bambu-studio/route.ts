import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

import { bambuStudioFilename, createBambuStudioFileToken, isSlicedBambuPrintFile } from "@/lib/bambuStudioLaunch";

const API_BASE_URL = getBackendBaseUrl();

type Preparation = {
  printer_id: number;
  printer_name?: string;
  recommended_slot?: { ams_id: number; tray_id: number } | null;
  color_distance?: number | null;
  warnings?: string[];
};

function externalOrigin(request: NextRequest) {
  const candidates = [
    request.headers.get("origin"),
    request.headers.get("x-forwarded-host")
      ? `${request.headers.get("x-forwarded-proto") || "http"}://${request.headers.get("x-forwarded-host")}`
      : null,
    new URL(request.url).origin,
  ];
  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      const url = new URL(candidate);
      if (url.protocol === "http:" || url.protocol === "https:") return url.origin;
    } catch {
      // Ignore malformed proxy headers and continue with the next candidate.
    }
  }
  throw new Error("Het externe websiteadres kon niet worden bepaald.");
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isInteger(productId) || productId <= 0) {
    return NextResponse.json({ detail: "Ongeldig productnummer" }, { status: 400 });
  }

  const productResponse = await backendFetch(`${API_BASE_URL}/products/${productId}`, { cache: "no-store" });
  const product = await productResponse.json().catch(() => null);
  if (!productResponse.ok || !product) {
    return NextResponse.json({ detail: product?.detail || "Product niet gevonden" }, { status: productResponse.status });
  }
  if (!product.print_file_path) {
    return NextResponse.json({ detail: "Koppel eerst een Bambu Studio-productbestand aan dit product." }, { status: 409 });
  }

  try {
    const payload = await request.json().catch(() => ({}));
    const sliced = isSlicedBambuPrintFile(product.print_file_path);
    const variantId = Number(payload.variant_id);
    const preferredPrinterId = Number(payload.printer_id);
    const printJobId = payload.print_job_id == null ? null : Number(payload.print_job_id);
    if (sliced && (!Number.isInteger(variantId) || variantId <= 0 || !Number.isInteger(preferredPrinterId) || preferredPrinterId <= 0)) {
      return NextResponse.json({ detail: "Kies eerst een productvariant en printer." }, { status: 400 });
    }
    if (printJobId !== null && (!Number.isInteger(printJobId) || printJobId <= 0)) {
      return NextResponse.json({ detail: "Ongeldig printtaaknummer." }, { status: 400 });
    }

    let preparation: Preparation | null = null;
    let printerId = preferredPrinterId;
    let amsId = -1;
    let trayId = -1;
    if (sliced) {
      const printersResponse = await backendFetch(`${API_BASE_URL}/bambu/printers`, { cache: "no-store" });
      const printers = await printersResponse.json().catch(() => []);
      if (!printersResponse.ok || !Array.isArray(printers)) {
        return NextResponse.json({ detail: "Printers konden niet worden geladen." }, { status: 503 });
      }
      const candidates = printers
        .filter((printer) => printer.active)
        .sort((left, right) => Number(right.id === preferredPrinterId) - Number(left.id === preferredPrinterId));
      const preparations: Preparation[] = [];
      let lastError = "Geen compatibele actieve printer gevonden.";
      for (const printer of candidates) {
        const preparationUrl = new URL(`${API_BASE_URL}/products/${productId}/print-file/preparation`);
        preparationUrl.searchParams.set("variant_id", String(variantId));
        preparationUrl.searchParams.set("printer_id", String(printer.id));
        const preparationResponse = await backendFetch(preparationUrl, { cache: "no-store" });
        const candidate = await preparationResponse.json().catch(() => null);
        if (preparationResponse.ok && candidate) preparations.push(candidate);
        else if (candidate?.detail) lastError = candidate.detail;
      }
      const matchingPreparations = preparations
        .filter((item) => item.recommended_slot)
        .sort((left, right) => Number(left.color_distance ?? 0) - Number(right.color_distance ?? 0));
      preparation = matchingPreparations[0] || preparations[0] || null;
      if (!preparation) return NextResponse.json({ detail: lastError }, { status: 409 });
      printerId = Number(preparation.printer_id);
      amsId = preparation.recommended_slot ? Number(preparation.recommended_slot.ams_id) : -1;
      trayId = preparation.recommended_slot ? Number(preparation.recommended_slot.tray_id) : -1;
    }
    const context = sliced ? `${variantId}:${printerId}:${amsId}:${trayId}` : "source";
    const filename = bambuStudioFilename(product.internal_title || product.name || `product-${productId}`, product.print_file_path);
    const token = await createBambuStudioFileToken(productId, filename, context);
    const fileUrlObject = new URL(`/api/bambu-studio/files/${token}/${filename}`, externalOrigin(request));
    if (sliced) {
      fileUrlObject.searchParams.set("variant_id", String(variantId));
      fileUrlObject.searchParams.set("printer_id", String(printerId));
      fileUrlObject.searchParams.set("ams_id", String(amsId));
      fileUrlObject.searchParams.set("tray_id", String(trayId));
    }
    const fileUrl = fileUrlObject.toString();
    if (printJobId !== null && preparation && Number.isInteger(variantId) && variantId > 0 && Number.isInteger(printerId) && printerId > 0) {
      const jobResponse = await backendFetch(`${API_BASE_URL}/print-jobs/${printJobId}/bambu-studio-opened`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ printer_id: printerId, product_id: productId, product_variant_id: variantId }),
      });
      if (!jobResponse.ok) {
        preparation.warnings = [...(preparation.warnings || []), "De printtaak kon niet automatisch als gepland worden opgeslagen."];
      }
    }
    return NextResponse.json({
      file_url: fileUrl,
      launcher_url: `printmanager://open?file=${encodeURIComponent(fileUrl)}`,
      protocol_url: `bambustudio://open?file=${encodeURIComponent(fileUrl)}`,
      expires_in_seconds: 600,
      preparation,
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Bambu Studio-link kon niet worden gemaakt" },
      { status: 503 },
    );
  }
}
