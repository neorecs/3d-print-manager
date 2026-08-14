import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

const exportPaths: Record<string, { path: string; filename: string }> = {
  sales: { path: "/accounting/sales/export.csv", filename: "verkoopboek.csv" },
  purchases: { path: "/accounting/purchases/export.csv", filename: "inkoopboek.csv" },
  "vat-summary": { path: "/accounting/vat-summary/export.csv", filename: "btw-samenvatting.csv" },
};

export async function GET(request: Request, { params }: { params: Promise<{ kind: string }> }) {
  const { kind } = await params;
  const target = exportPaths[kind];

  if (!target) {
    return NextResponse.json({ detail: "Onbekende administratie-export" }, { status: 404 });
  }

  const incomingUrl = new URL(request.url);
  const query = incomingUrl.searchParams.toString();
  const response = await backendFetch(`${API_BASE_URL}${target.path}${query ? `?${query}` : ""}`, { cache: "no-store" });
  const content = await response.text();

  return new NextResponse(content, {
    status: response.status,
    headers: {
      "Content-Disposition": `attachment; filename="${target.filename}"`,
      "Content-Type": response.headers.get("content-type") || "text/csv; charset=utf-8",
    },
  });
}
