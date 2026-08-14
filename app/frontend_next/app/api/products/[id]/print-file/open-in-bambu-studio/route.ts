import { NextRequest, NextResponse } from "next/server";

import { bambuStudioFilename, createBambuStudioFileToken } from "@/lib/bambuStudioLaunch";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

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

  const productResponse = await fetch(`${API_BASE_URL}/products/${productId}`, { cache: "no-store" });
  const product = await productResponse.json().catch(() => null);
  if (!productResponse.ok || !product) {
    return NextResponse.json({ detail: product?.detail || "Product niet gevonden" }, { status: productResponse.status });
  }
  if (!product.print_file_path) {
    return NextResponse.json({ detail: "Koppel eerst een printklaar .gcode.3mf bestand aan dit product." }, { status: 409 });
  }

  try {
    const filename = bambuStudioFilename(product.internal_title || product.name || `product-${productId}`);
    const token = await createBambuStudioFileToken(productId, filename);
    const fileUrl = new URL(`/api/bambu-studio/files/${token}/${filename}`, externalOrigin(request)).toString();
    return NextResponse.json({
      file_url: fileUrl,
      launcher_url: `printmanager://open?file=${encodeURIComponent(fileUrl)}`,
      protocol_url: `bambustudio://open?file=${encodeURIComponent(fileUrl)}`,
      expires_in_seconds: 600,
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Bambu Studio-link kon niet worden gemaakt" },
      { status: 503 },
    );
  }
}
