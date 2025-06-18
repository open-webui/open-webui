// __tests__/middleware.test.ts
import { middleware } from '../src/middleware'; // Adjust path if middleware is not in src/
import { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

// Mock Supabase getSession to control auth state
jest.mock('@supabase/ssr', () => ({
  ...jest.requireActual('@supabase/ssr'), // Import and retain default behavior
  createServerClient: jest.fn().mockReturnValue({
    auth: {
      getSession: jest.fn(),
    },
  }),
}));

// Mock next/headers cookies()
jest.mock('next/headers', () => ({
    cookies: jest.fn(() => ({
        get: jest.fn(),
        set: jest.fn(),
        // Add other methods if your middleware uses them extensively
    })),
}));


describe('Middleware', () => {
  it('should redirect unauthenticated user from protected route to /login', async () => {
    const { createServerClient } = require('@supabase/ssr');
    (createServerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: null }, error: null });

    const req = new NextRequest(new URL('/chat', 'http://localhost')); // Example protected route
    const response = await middleware(req);

    expect(response).toBeInstanceOf(NextResponse);
    if (response instanceof NextResponse) {
        expect(response.status).toBe(307); // Or 302, depending on NextResponse.redirect default
        expect(response.headers.get('location')).toContain('/login');
    }
  });

  it('should allow authenticated user to access protected route', async () => {
    const { createServerClient } = require('@supabase/ssr');
    (createServerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: { user: { id: '123' } } }, error: null });

    const req = new NextRequest(new URL('/chat', 'http://localhost'));
    const response = await middleware(req);

    expect(response).toBeInstanceOf(NextResponse); // Should be NextResponse.next()
    // Check that it's not a redirect
    expect(response.headers.get('location')).toBeNull();
  });

  it('should redirect authenticated user from /login to /', async () => {
    const { createServerClient } = require('@supabase/ssr');
    (createServerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: { user: { id: '123' } } }, error: null });

    const req = new NextRequest(new URL('/login', 'http://localhost'));
    const response = await middleware(req);

    expect(response).toBeInstanceOf(NextResponse);
    if (response instanceof NextResponse) {
        expect(response.status).toBe(307);
        expect(response.headers.get('location')).toBe('http://localhost/');
    }
  });
});
