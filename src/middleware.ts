// src/middleware.ts
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          // If the cookie is set, update the request and response
          request.cookies.set({ name, value, ...options });
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          });
          response.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          // If the cookie is deleted, update the request and response
          request.cookies.set({ name, value: '', ...options });
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          });
          response.cookies.set({ name, value: '', ...options });
        },
      },
    }
  );

  // Refresh session if expired - important to keep RLS working correctly
  const { data: { session } } = await supabase.auth.getSession();

  const { pathname } = request.nextUrl;

  // Define protected and public routes
  // Assuming (main) is a route group, so paths are directly under /
  const protectedRoutes = ['/chat', '/history', '/settings', '/usage'];
  const authRoutes = ['/login', '/signup']; // Auth pages

  // If user is not logged in and trying to access a protected route
  if (!session && protectedRoutes.some(route => pathname.startsWith(route))) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = '/login';
    redirectUrl.searchParams.set('redirectedFrom', pathname);
    console.log(`Redirecting unauthenticated user from ${pathname} to /login`);
    return NextResponse.redirect(redirectUrl);
  }

  // If user is logged in and trying to access an auth route (like /login)
  if (session && authRoutes.some(route => pathname.startsWith(route))) {
    console.log(`Redirecting authenticated user from ${pathname} to /`);
    return NextResponse.redirect(new URL('/', request.url)); // Redirect to home page
  }

  // If user is not logged in and trying to access root, let them (e.g. if root is a landing page)
  // or redirect to login if root is also protected. For this setup, assuming root ('/') could be public or redirect handled by page itself.
  // If you want to protect the root page, add '/' to protectedRoutes.

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - api/auth/callback (Supabase auth callback) - IMPORTANT to exclude this
     * - api/ (other API routes if they don't need auth or handle it differently) - adjust as needed
     * Feel free to modify this pattern to include more paths.
     */
    '/((?!_next/static|_next/image|favicon.ico|api/auth/callback|api/chat/stream).*)',
  ],
};
