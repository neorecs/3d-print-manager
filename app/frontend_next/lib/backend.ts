export function getBackendBaseUrl() {
  return process.env.API_BASE_URL || process.env.FRONTEND_NEXT_API_BASE_URL || "http://backend:8000";
}


export async function backendFetch(input: string | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const internalToken = process.env.BACKEND_INTERNAL_TOKEN;
  if (!internalToken) {
    throw new Error("BACKEND_INTERNAL_TOKEN ontbreekt in de Next.js-configuratie.");
  }
  headers.set("X-Backend-Internal-Token", internalToken);

  return fetch(input, { ...init, headers });
}
