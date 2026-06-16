import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js middleware for session-aware route protection.
 *
 * Session states:
 * - unauthenticated: no access_token cookie → redirect to /login
 * - authenticated: has access_token → redirect away from /auth/* to /dashboard
 *
 * Public routes: /auth/*, /.well-known/*, /catalog/access, / (home page)
 * Protected routes: /dashboard/*, /generate/*, /batches/*, /extraction/*, /media/*, /jobs/*
 */
export function proxy(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value;
  const { pathname } = request.nextUrl;

  // Public routes — no redirect needed
  const isPublicRoute =
    pathname.startsWith("/auth") ||
    pathname.startsWith("/.well-known") ||
    pathname === "/" ||
    pathname.startsWith("/catalog/access");

  // Protected routes that require authentication
  const isProtectedRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/generate") ||
    pathname.startsWith("/batches") ||
    pathname.startsWith("/extraction") ||
    pathname.startsWith("/media") ||
    pathname.startsWith("/jobs");

  // If authenticated and trying to access auth pages → redirect to dashboard
  if (token && pathname.startsWith("/auth")) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // If unauthenticated and trying to access protected route → redirect to login
  if (!token && isProtectedRoute) {
    const loginUrl = new URL("/login", request.url);
    // Preserve the original path for post-login redirect
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/registro",
    "/auth/:path*",
    "/dashboard/:path*",
    "/generate/:path*",
    "/batches/:path*",
    "/extraction/:path*",
    "/media/:path*",
    "/jobs/:path*",
  ],
};
