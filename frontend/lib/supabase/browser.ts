'use client';

import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';
import { isSupabaseAuthEnabled, supabasePublicConfig } from '@/lib/supabase/env';

let client: SupabaseClient | null = null;

export function supabaseBrowser(): SupabaseClient {
  if (!isSupabaseAuthEnabled()) {
    throw new Error('Supabase auth is not configured');
  }
  if (!client) {
    const { url, anonKey } = supabasePublicConfig();
    client = createBrowserClient(url, anonKey);
  }
  return client;
}
