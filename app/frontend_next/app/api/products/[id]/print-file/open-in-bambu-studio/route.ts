import { backendFetch,getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest,NextResponse } from "next/server";

import { bambuStudioFilename,createBambuStudioFileToken,isSlicedBambuPrintFile } from "@/lib/bambuStudioLaunch";

const API_BASE_URL=getBackendBaseUrl();

type Preparation={
  printer_id: number;
  printer_name?: string;
  recommended_slot?: { ams_id: number; tray_id: number }|null;
  color_distance?: number|null;
  warnings?: string[];
  last_seen_at?: string|null;
};

function externalOrigin(request: NextRequest) {
  const candidates=[
    request.headers.get("origin"),
    request.headers.get("x-forwarded-host")
      ? `${request.headers.get("x-forwarded-proto")||"http"}://${request.headers.get("x-forwarded-host")}`
      :null,
    new URL(request.url).origin,
  ];
  for(const candidate of candidates) {
    if(!candidate) continue;
    try {
      const url=new URL(candidate);
      if(url.protocol==="http:"||url.protocol==="https:") return url.origin;
    } catch {
      // Ignore malformed proxy headers and continue with the next candidate.
    }
  }
  throw new Error("Het externe websiteadres kon niet worden bepaald.");
}

export async function POST(request: NextRequest,{ params }: { params: Promise<{ id: string }> }) {
  const { id }=await params;
  const productId=Number(id);
  if(!Number.isInteger(productId)||productId<=0) {
    return NextResponse.json({ detail: "Ongeldig productnummer" },{ status: 400 });
  }

  const productResponse=await backendFetch(`${API_BASE_URL}/products/${productId}`,{ cache: "no-store" });
  const product=await productResponse.json().catch(() => null);
  if(!productResponse.ok||!product) {
    return NextResponse.json({ detail: product?.detail||"Product niet gevonden" },{ status: productResponse.status });
  }
  if(!product.print_file_path) {
    return NextResponse.json({ detail: "Koppel eerst een Bambu Studio-productbestand aan dit product." },{ status: 409 });
  }

  try {
    const payload=await request.json().catch(() => ({}));
    const sliced=isSlicedBambuPrintFile(product.print_file_path);
    const variantId=Number(payload.variant_id);
    const preferredPrinterId=Number(payload.printer_id);
    const printJobId=payload.print_job_id==null? null:Number(payload.print_job_id);
    if(printJobId!==null&&(!Number.isInteger(printJobId)||printJobId<=0)) {
      return NextResponse.json({ detail: "Ongeldig printtaaknummer." },{ status: 400 });
    }
    if(printJobId!==null&&(!Number.isInteger(variantId)||variantId<=0)) {
      return NextResponse.json({ detail: "De productvariant van de printtaak ontbreekt." },{ status: 400 });
    }

    let preparation: Preparation|null=null;
    const warnings: string[]=[];
    // Advice uses cached telemetry and has one bounded budget; opening never depends on it.
    if(sliced&&Number.isInteger(variantId)&&variantId>0) {
      try {
        const signal=AbortSignal.timeout(3000);
        const printersResponse=await backendFetch(`${API_BASE_URL}/bambu/printers`,{ cache: "no-store",signal });
        const printers=await printersResponse.json().catch(() => []);
        if(!printersResponse.ok||!Array.isArray(printers)) {
          throw new Error("Printeradvies is niet beschikbaar.");
        }
        const candidates=printers
          .filter((printer) => printer.active)
          .sort((left,right) => Number(right.id===preferredPrinterId)-Number(left.id===preferredPrinterId));
        const preparations: Preparation[]=[];
        let lastError="Geen compatibele actieve printer gevonden.";
        for(const printer of candidates) {
          const preparationUrl=new URL(`${API_BASE_URL}/products/${productId}/print-file/preparation`);
          preparationUrl.searchParams.set("variant_id",String(variantId));
          preparationUrl.searchParams.set("printer_id",String(printer.id));
          const preparationResponse=await backendFetch(preparationUrl,{ cache: "no-store",signal });
          const candidate=await preparationResponse.json().catch(() => null);
          if(preparationResponse.ok&&candidate) preparations.push({ ...candidate,last_seen_at: printer.last_seen_at });
          else if(candidate?.detail) lastError=candidate.detail;
        }
        const matchingPreparations=preparations
          .filter((item) => item.recommended_slot)
          .sort((left,right) => Number(left.color_distance??0)-Number(right.color_distance??0));
        preparation=matchingPreparations[0]||preparations[0]||null;
        if(!preparation) warnings.push(lastError);
      } catch {
        warnings.push("Printeradvies is niet beschikbaar. Kies printer en filament in Bambu Studio.");
      }
    }
    const context="source";
    const filename=bambuStudioFilename(product.internal_title||product.name||`product-${productId}`,product.print_file_path);
    const token=await createBambuStudioFileToken(productId,filename,context);
    const fileUrlObject=new URL(`/api/bambu-studio/files/${token}/${filename}`,externalOrigin(request));
    fileUrlObject.searchParams.set("mode","source");
    const fileUrl=fileUrlObject.toString();
    if(printJobId!==null&&Number.isInteger(variantId)&&variantId>0) {
      try {
        const jobResponse=await backendFetch(`${API_BASE_URL}/print-jobs/${printJobId}/bambu-studio-opened`,{
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ printer_id: preparation?.printer_id??null,product_id: productId,product_variant_id: variantId }),
          signal: AbortSignal.timeout(5000),
        });
        if(!jobResponse.ok) {
          throw new Error("Planning niet opgeslagen");
        }
      } catch {
        warnings.push("De overdracht kon niet bij de printtaak worden opgeslagen. Controleer de printplanning.");
      }
    }
    return NextResponse.json({
      file_url: fileUrl,
      launcher_url: `printmanager://open?file=${encodeURIComponent(fileUrl)}`,
      protocol_url: `bambustudio://open?file=${encodeURIComponent(fileUrl)}`,
      expires_in_seconds: 600,
      preparation,
      warnings,
    });
  } catch(error) {
    return NextResponse.json(
      { detail: error instanceof Error? error.message:"Bambu Studio-link kon niet worden gemaakt" },
      { status: 503 },
    );
  }
}
