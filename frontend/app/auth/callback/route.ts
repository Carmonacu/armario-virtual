import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { supabasePublicConfig } from '@/lib/supabase/env';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const next = url.searchParams.get('next') || '/dashboard';
  const destination = new URL(next, url.origin);

  if (!code) {
    destination.pathname = '/login';
    destination.search = 'error=Callback';
    return NextResponse.redirect(destination);
  }

  const cookieStore = cookies();
  const { url: supabaseUrl, anonKey } = supabasePublicConfig();
  const supabase = createServerClient(supabaseUrl, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          cookieStore.set(name, value, options);
        });
      },
    },
  });

  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    destination.pathname = '/login';
    destination.search = 'error=Callback';
    return NextResponse.redirect(destination);
  }

  destination.search = '';
  return NextResponse.redirect(destination);
}
