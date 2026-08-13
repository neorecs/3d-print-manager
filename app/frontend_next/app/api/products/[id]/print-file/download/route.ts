const API_BASE_URL = process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await fetch(`${API_BASE_URL}/products/${id}/print-file/download`, { cache: "no-store" });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    return Response.json(data || { detail: "Printbestand kon niet worden gedownload" }, { status: response.status });
  }
  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/octet-stream",
      "content-disposition": response.headers.get("content-disposition") || "attachment",
      "content-length": response.headers.get("content-length") || "",
      "cache-control": "private, no-store",
    },
  });
}
