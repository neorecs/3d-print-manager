import { backendFetch, getBackendBaseUrl } from "@/lib/backend";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = getBackendBaseUrl();

// Print file for one queued print command, streamed to the bridge agent.
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return NextResponse.json({ detail: "Bestand niet gevonden." }, { status: 404 });
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  const response = await backendFetch(`${API_BASE_URL}/bridge-agent/files/${id}`, { headers });
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({ detail: "Bestand niet gevonden." }));
    return NextResponse.json(data, { status: response.status });
  }
  const out = new Headers({ "Content-Type": "application/octet-stream" });
  const length = response.headers.get("content-length");
  if (length) out.set("Content-Length", length);
  return new Response(response.body, { status: 200, headers: out });
}
