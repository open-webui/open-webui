// TODO: Add more robust error handling and logging
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic'; // Ensures this route is always dynamic

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');

  if (code) {
    const supabase = createRouteHandlerClient({ cookies });
    try {
        await supabase.auth.exchangeCodeForSession(code);
        // URL to redirect to after successful sign in
        // Usually your main application page
        return NextResponse.redirect(new URL('/', request.url).toString());
    } catch (error) {
        console.error('Auth callback error:', error);
        // URL to redirect to on error
        return NextResponse.redirect(new URL('/login?error=auth_callback_failed', request.url).toString());
    }
  } else {
    console.error('No code found in auth callback request');
     // URL to redirect to on error (e.g. no code)
    return NextResponse.redirect(new URL('/login?error=no_code_provided', request.url).toString());
  }
}
