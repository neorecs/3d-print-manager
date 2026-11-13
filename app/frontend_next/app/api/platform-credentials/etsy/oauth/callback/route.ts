import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";
import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = getBackendBaseUrl();

// Etsy sends the browser back here after the seller approved (or refused) access.
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const target = request.nextUrl.clone();
  target.search = "";

  if (!code || !state) {
    target.pathname = "/verkoopkanalen";
    target.searchParams.set("etsy", "geweigerd");
    return NextResponse.redirect(target);
  }

  const response = await backendFetch(`${API_BASE_URL}/platform-credentials/etsy/oauth/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.platform_id) {
    target.pathname = "/verkoopkanalen";
    target.searchParams.set("etsy", "fout");
    return NextResponse.redirect(target);
  }
  target.pathname = `/verkoopkanalen/${data.platform_id}`;
  target.searchParams.set("etsy", "verbonden");
  return NextResponse.redirect(target);
}
