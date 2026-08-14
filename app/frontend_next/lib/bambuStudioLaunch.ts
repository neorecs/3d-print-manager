const TOKEN_LIFETIME_SECONDS = 10 * 60;

function getSecret() {
  return process.env.AUTH_SECRET || "";
}

function base64UrlEncode(value: ArrayBuffer) {
  const bytes = new Uint8Array(value);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function sign(value: string, secret: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return base64UrlEncode(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
}

function constantTimeEqual(left: string, right: string) {
  if (left.length !== right.length) return false;
  let result = 0;
  for (let index = 0; index < left.length; index += 1) {
    result |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return result === 0;
}

function signatureValue(productId: number, expiresAt: number, filename: string) {
  return `${productId}:${expiresAt}:${filename}`;
}

export async function createBambuStudioFileToken(productId: number, filename: string) {
  const secret = getSecret();
  if (!secret) throw new Error("De beveiligingssleutel voor Bambu Studio-links ontbreekt.");
  const expiresAt = Math.floor(Date.now() / 1000) + TOKEN_LIFETIME_SECONDS;
  const signature = await sign(signatureValue(productId, expiresAt, filename), secret);
  return `${productId}.${expiresAt}.${signature}`;
}

export async function verifyBambuStudioFileToken(token: string, filename: string) {
  const secret = getSecret();
  const [productIdValue, expiresAtValue, signature] = token.split(".");
  const productId = Number(productIdValue);
  const expiresAt = Number(expiresAtValue);
  if (!secret || !Number.isInteger(productId) || productId <= 0 || !Number.isInteger(expiresAt) || !signature) return null;
  if (expiresAt < Math.floor(Date.now() / 1000)) return null;
  const expected = await sign(signatureValue(productId, expiresAt, filename), secret);
  return constantTimeEqual(signature, expected) ? { productId, expiresAt } : null;
}

export function bambuStudioFilename(name: string) {
  const base = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "") || "product";
  return `${base}.gcode.3mf`;
}
