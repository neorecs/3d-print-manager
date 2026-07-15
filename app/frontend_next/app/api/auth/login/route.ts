import { NextRequest, NextResponse } from "next/server";

import { authIsConfigured, setSessionCookie, validateLogin } from "@/lib/auth";

const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const LOGIN_MAX_ATTEMPTS = 5;
const loginAttempts = new Map<string, { count: number; resetAt: number }>();

function getRateLimitKey(request: NextRequest, email: string) {
  const forwardedFor = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const realIp = request.headers.get("x-real-ip");
  const ipAddress = forwardedFor || realIp || "unknown";
  return `${ipAddress}:${email.trim().toLowerCase()}`;
}

function isRateLimited(key: string) {
  const now = Date.now();
  const current = loginAttempts.get(key);
  if (!current || current.resetAt <= now) {
    loginAttempts.set(key, { count: 1, resetAt: now + LOGIN_WINDOW_MS });
    return false;
  }

  current.count += 1;
  loginAttempts.set(key, current);
  return current.count > LOGIN_MAX_ATTEMPTS;
}

function clearRateLimit(key: string) {
  loginAttempts.delete(key);
}

export async function POST(request: NextRequest) {
  if (!authIsConfigured()) {
    return NextResponse.json({ detail: "Auth is niet volledig geconfigureerd." }, { status: 503 });
  }

  const payload = await request.json().catch(() => ({}));
  const email = typeof payload.email === "string" ? payload.email : "";
  const password = typeof payload.password === "string" ? payload.password : "";
  const mfaCode = typeof payload.mfaCode === "string" ? payload.mfaCode : "";
  const rateLimitKey = getRateLimitKey(request, email);

  if (isRateLimited(rateLimitKey)) {
    return NextResponse.json({ detail: "Te veel loginpogingen. Probeer het later opnieuw." }, { status: 429 });
  }

  const result = await validateLogin(email, password, mfaCode);
  if (!result.ok) {
    if (result.mfaRequired) {
      return NextResponse.json({ detail: result.error || "MFA-code vereist.", mfa_required: true }, { status: 401 });
    }
    return NextResponse.json({ detail: result.error || "Inloggen mislukt." }, { status: 401 });
  }

  clearRateLimit(rateLimitKey);
  const response = NextResponse.json({ email: result.email, name: result.name, role: result.role });
  return setSessionCookie(response, result.email, result.name, result.role);
}
