import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
const API_BASE_URL = getBackendBaseUrl();

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await backendFetch(`${API_BASE_URL}/products/${id}/print-file/download`, { cache: "no-store" });
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
