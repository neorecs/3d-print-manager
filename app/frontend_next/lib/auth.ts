import { NextRequest, NextResponse } from "next/server";

export const AUTH_COOKIE_NAME = "print_manager_session";
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 12;

type SessionPayload = {
  email: string;
  name: string;
  role: "admin" | "operator" | "viewer";
  exp: number;
};

function isAuthEnabled() {
  return process.env.AUTH_ENABLED === "true";
}

function getAuthSecret() {
  return process.env.AUTH_SECRET || "";
}

function base64UrlEncode(value: string | ArrayBuffer) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : new Uint8Array(value);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlDecode(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

async function sign(value: string, secret: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return base64UrlEncode(signature);
}

async function createSessionToken(payload: SessionPayload, secret: string) {
  const body = base64UrlEncode(JSON.stringify(payload));
  const signature = await sign(body, secret);
  return `${body}.${signature}`;
}

function constantTimeEqual(left: string, right: string) {
  if (left.length !== right.length) return false;

  let result = 0;
  for (let index = 0; index < left.length; index += 1) {
    result |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return result === 0;
}

export function authIsConfigured() {
  if (!isAuthEnabled()) return true;
  if (process.env.AUTH_BACKEND_LOGIN === "true") {
    return Boolean(getAuthSecret());
  }
  return Boolean(getAuthSecret() && process.env.AUTH_ADMIN_EMAIL && process.env.AUTH_ADMIN_PASSWORD);
}

export function authIsEnabled() {
  return isAuthEnabled();
}

type LoginResult =
  | { ok: true; email: string; name: string; role: SessionPayload["role"] }
  | { ok: false; error: string; mfaRequired?: boolean };

export async function verifySessionToken(token?: string | null): Promise<SessionPayload | null> {
  if (!isAuthEnabled()) {
    return {
      email: "dev@local",
      name: "Lokale gebruiker",
      role: "admin",
      exp: Math.floor(Date.now() / 1000) + SESSION_MAX_AGE_SECONDS,
    };
  }

  const secret = getAuthSecret();
  if (!token || !secret || !token.includes(".")) return null;

  const [body, signature] = token.split(".");
  const expectedSignature = await sign(body, secret);
  if (!constantTimeEqual(signature, expectedSignature)) return null;

  try {
    const payload = JSON.parse(base64UrlDecode(body)) as SessionPayload;
    if (!payload.email || !payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

export async function getSessionFromRequest(request: NextRequest) {
  return verifySessionToken(request.cookies.get(AUTH_COOKIE_NAME)?.value);
}

export async function getSessionFromCookieStore(cookieValue?: string | null) {
  return verifySessionToken(cookieValue);
}

export async function validateLogin(email: string, password: string, mfaCode?: string): Promise<LoginResult> {
  if (process.env.AUTH_BACKEND_LOGIN === "true") {
    return validateBackendLogin(email, password, mfaCode);
  }

  if (!isAuthEnabled()) {
    return { ok: true, email: "dev@local", name: "Lokale gebruiker", role: "admin" };
  }

  const expectedEmail = process.env.AUTH_ADMIN_EMAIL;
  const expectedPassword = process.env.AUTH_ADMIN_PASSWORD;
  if (!expectedEmail || !expectedPassword || !getAuthSecret()) {
    return { ok: false, error: "Auth is niet volledig geconfigureerd." };
  }

  if (email.trim().toLowerCase() !== expectedEmail.trim().toLowerCase() || password !== expectedPassword) {
    return { ok: false, error: "E-mailadres of wachtwoord klopt niet." };
  }

  return { ok: true, email: expectedEmail, name: process.env.AUTH_ADMIN_NAME || "Beheerder", role: "admin" };
}

async function validateBackendLogin(email: string, password: string, mfaCode?: string): Promise<LoginResult> {
  const apiBaseUrl =
    process.env.FRONTEND_NEXT_API_BASE_URL || process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, mfa_code: mfaCode || null }),
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug." }));
  if (!response.ok) {
    const detail = data.detail || "Inloggen mislukt.";
    if (typeof detail === "object" && detail?.mfa_required) {
      return { ok: false, error: detail.message || "MFA-code vereist.", mfaRequired: true };
    }
    return { ok: false, error: typeof detail === "string" ? detail : "Inloggen mislukt." };
  }

  return {
    ok: true,
    email: data.user.email,
    name: data.user.display_name || data.user.email,
    role: data.user.role || "viewer",
  };
}

export async function setSessionCookie(response: NextResponse, email: string, name: string, role: SessionPayload["role"] = "admin") {
  const secret = getAuthSecret();
  if (!secret) return response;

  const exp = Math.floor(Date.now() / 1000) + SESSION_MAX_AGE_SECONDS;
  const token = await createSessionToken({ email, name, role, exp }, secret);

  response.cookies.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  return response;
}

export function clearSessionCookie(response: NextResponse) {
  response.cookies.set(AUTH_COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return response;
}
