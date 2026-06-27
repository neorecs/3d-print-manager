import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

const exportPaths: Record<string, { path: string; filename: string }> = {
  sales: { path: "/accounting/sales/export.csv", filename: "verkoopboek.csv" },
  purchases: { path: "/accounting/purchases/export.csv", filename: "inkoopboek.csv" },
  "vat-summary": { path: "/accounting/vat-summary/export.csv", filename: "btw-samenvatting.csv" },
};

export async function GET(_request: Request, { params }: { params: Promise<{ kind: string }> }) {
  const { kind } = await params;
  const target = exportPaths[kind];

  if (!target) {
    return NextResponse.json({ detail: "Onbekende administratie-export" }, { status: 404 });
  }

  const response = await fetch(`${API_BASE_URL}${target.path}`, { cache: "no-store" });
  const content = await response.text();

  return new NextResponse(content, {
    status: response.status,
    headers: {
      "Content-Disposition": `attachment; filename="${target.filename}"`,
      "Content-Type": response.headers.get("content-type") || "text/csv; charset=utf-8",
    },
  });
}
