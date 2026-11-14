import { backendFetch, getBackendBaseUrl } from "@/lib/backend";
import { NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();
// Only the headers the backend needs to check the platform signature.
const FORWARDED_HEADERS = ["content-type", "x-shopify-hmac-sha256", "x-shopify-topic", "x-shopify-webhook-id", "webhook-id", "webhook-timestamp", "webhook-signature"];

type Params = { params: Promise<{ platform: string; id: string }> };

export async function POST(request: Request, { params }: Params) {
  const { platform, id } = await params;
  if (!/^[a-z]+$/.test(platform) || !/^\d+$/.test(id)) {
    return NextResponse.json({ detail: "Onbekende webhook." }, { status: 404 });
  }
  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  // The raw body must reach the backend unchanged, otherwise the signature no longer matches.
  const body = await request.arrayBuffer();
  const response = await backendFetch(`${API_BASE_URL}/webhooks/${platform}/${id}`, { method: "POST", headers, body });
  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
