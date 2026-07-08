import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js proxy: request-id tagging + session-aware route protection.
 *
 * Session states:
 * - unauthenticated: no access_token cookie → redirect to /login
 * - authenticated: has access_token → redirect away from /auth/* to /dashboard
 *
 * Public routes: /auth/*, /.well-known/*, /catalog/access, / (home page)
 * Protected routes: /dashboard/*, /generate/*, /batches/*, /extraction/*, /media/*, /jobs/*
 */
export function proxy(request: NextRequest) {
  const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-request-id", requestId);

  const token = request.cookies.get("access_token")?.value;
  const { pathname } = request.nextUrl;

  // If authenticated and trying to access auth pages → redirect to dashboard
  if (token && pathname.startsWith("/auth")) {
    const response = NextResponse.redirect(new URL("/dashboard", request.url));
    response.headers.set("x-request-id", requestId);
    return response;
  }

  // Protected routes that require authentication
  const isProtectedRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/generate") ||
    pathname.startsWith("/batches") ||
    pathname.startsWith("/extraction") ||
    pathname.startsWith("/media") ||
    pathname.startsWith("/jobs");

  // If unauthenticated and trying to access protected route → redirect to login
  if (!token && isProtectedRoute) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    const response = NextResponse.redirect(loginUrl);
    response.headers.set("x-request-id", requestId);
    return response;
  }

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  response.headers.set("x-request-id", requestId);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico).*)"],
};
