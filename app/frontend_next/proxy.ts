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
];

function isPublicPath(pathname: string) {
  return publicPaths.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export async function proxy(request: NextRequest) {
  if (!authIsEnabled() || isPublicPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const session = await getSessionFromRequest(request);
  if (session) {
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
