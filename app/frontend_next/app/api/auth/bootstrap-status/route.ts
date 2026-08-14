import { NextResponse } from "next/server";
import { backendFetch, getBackendBaseUrl } from "@/lib/backend-auth";


export async function GET() {
  const response = await backendFetch(`${getBackendBaseUrl()}/auth/bootstrap-status`, { cache: "no-store" });
  const data = await response.json().catch(() => ({ available: false }));
  return NextResponse.json(data, { status: response.status });
}
