import "server-only";

import { cookies } from "next/headers";
import { backendFetch as internalBackendFetch, getBackendBaseUrl } from "./backend";

const SESSION_COOKIE_NAME = "print_manager_session";

export { getBackendBaseUrl };

export async function backendFetch(input: string | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (sessionToken && !headers.has("X-Session-Token")) {
    headers.set("X-Session-Token", sessionToken);
  }
  return internalBackendFetch(input, { ...init, headers });
}
