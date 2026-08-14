import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
const API_BASE_URL = getBackendBaseUrl();

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await backendFetch(`${API_BASE_URL}/print-batches/${id}/export/download`, { cache: "no-store" });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    return Response.json(data || { detail: "Bambu Studio-pakket kon niet worden gedownload" }, { status: response.status });
  }
  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": "application/zip",
      "content-disposition": response.headers.get("content-disposition") || `attachment; filename="batch-${id}-bambu-studio.zip"`,
      "content-length": response.headers.get("content-length") || "",
      "cache-control": "private, no-store",
    },
  });
}
