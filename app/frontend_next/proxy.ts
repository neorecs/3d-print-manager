import { NextRequest, NextResponse } from "next/server";

import { getSessionFromRequest, authIsEnabled } from "./lib/auth";

const publicPaths = [
  "/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/session",
  "/api/auth/bootstrap-admin",
  "/api/auth/change-password",
  "/api/health",
  "/api/bambu-studio/files",
];

function isPublicPath(pathname: string) {
  return publicPaths.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

function roleDenied(request: NextRequest, role: "admin" | "operator" | "viewer") {
  const pathname = request.nextUrl.pathname;
  const mutating = !["GET", "HEAD", "OPTIONS"].includes(request.method.toUpperCase());

  if (role === "viewer" && mutating) {
    return "Een viewer mag alleen gegevens bekijken.";
  }
  if (role !== "admin") {
    const adminOnlyPrefixes = [
      "/instellingen/gebruikers",
      "/api/auth/users",
      "/api/auth/audit-logs",
      "/api/platform-credentials",
      "/api/accounting/fiscal-settings",
    ];
    if (adminOnlyPrefixes.some((prefix) => pathname.startsWith(prefix))) {
      return "Deze actie is alleen beschikbaar voor een beheerder.";
    }
    if (pathname.includes("/credentials")) {
      return "Verkoopkanaal-credentials mogen alleen door een beheerder worden aangepast.";
    }
  }
  return null;
}

export async function proxy(request: NextRequest) {
  if (!authIsEnabled() || isPublicPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const session = await getSessionFromRequest(request);
  if (session) {
    const deniedMessage = roleDenied(request, session.role);
    if (deniedMessage) {
      if (request.nextUrl.pathname.startsWith("/api/")) {
        return NextResponse.json({ detail: deniedMessage }, { status: 403 });
      }
      const target = request.nextUrl.clone();
      target.pathname = "/";
      target.searchParams.set("toegang", "geweigerd");
      return NextResponse.redirect(target);
    }
    if (
      session.mustChangePassword &&
      request.nextUrl.pathname !== "/account/wachtwoord-wijzigen" &&
      !request.nextUrl.pathname.startsWith("/api/auth/change-password") &&
      !request.nextUrl.pathname.startsWith("/api/auth/logout") &&
      !request.nextUrl.pathname.startsWith("/api/auth/session")
    ) {
      if (request.nextUrl.pathname.startsWith("/api/")) {
        return NextResponse.json({ detail: "Wijzig eerst je tijdelijke wachtwoord." }, { status: 403 });
      }
      const changeUrl = request.nextUrl.clone();
      changeUrl.pathname = "/account/wachtwoord-wijzigen";
      changeUrl.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
      return NextResponse.redirect(changeUrl);
    }
    return NextResponse.next();
  }

  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Niet ingelogd." }, { status: 401 });
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
