export function isSupabaseAuthEnabled(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export function supabasePublicConfig(): { url: string; anonKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error('Supabase auth is not configured');
  }
  return { url, anonKey };
}

const OAUTH_PROVIDERS = ['google', 'github'] as const;
export type SupabaseOAuthProvider = (typeof OAUTH_PROVIDERS)[number];

export function supabaseOAuthProviders(): SupabaseOAuthProvider[] {
  const allowed = new Set<string>(OAUTH_PROVIDERS);
  return (process.env.NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter((item): item is SupabaseOAuthProvider => allowed.has(item));
}
