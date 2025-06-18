// lib/supabase/server.ts
import { createServerClient, type CookieOptions } from '@supabase/ssr'; // Recommended for App Router
import { cookies } from 'next/headers';
import type { Database } from '../types_db'; // Assuming types_db.ts

export const createSupabaseServerClient = (cookieStore: ReturnType<typeof cookies>) => {
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!, // For server actions, route handlers this can be SUPABASE_URL
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, // Can be SUPABASE_SERVICE_ROLE_KEY for privileged operations
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options });
          } catch (error) {
            // The `set` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing
            // user sessions.
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: '', ...options });
          } catch (error) {
            // The `delete` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing
            // user sessions.
          }
        },
      },
    }
  );
};

// Helper for Route Handlers and Server Actions (where you don't pass cookieStore directly)
// This version reads the cookies directly from next/headers
export const createSupabaseRouteHandlerClient = () => {
    const cookieStore = cookies();
    return createServerClient<Database>( // Using createServerClient here as well
        process.env.NEXT_PUBLIC_SUPABASE_URL!, // For server actions, route handlers this can be SUPABASE_URL
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, // Can be SUPABASE_SERVICE_ROLE_KEY for privileged operations
        {
            cookies: {
                get(name: string) {
                    return cookieStore.get(name)?.value;
                },
                set(name: string, value: string, options: CookieOptions) {
                    cookieStore.set({ name, value, ...options });
                },
                remove(name: string, options: CookieOptions) {
                    cookieStore.set({ name, value: '', ...options });
                },
            },
        }
    );
};
