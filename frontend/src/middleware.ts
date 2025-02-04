import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // Skip middleware during static generation
  if (request.headers.get("x-middleware-prefetch")) {
    return NextResponse.next();
  }

  const token = request.cookies.get("token");
  const path = request.nextUrl.pathname;

  // Protect dashboard routes
  if (!token && path.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Redirect authenticated users away from auth pages
  // Only redirect if explicitly on the auth page, not other root routes
  if (token && path === "/") {
    console.log("Redirecting to dashboard", token);
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/dashboard/:path*"],
};
