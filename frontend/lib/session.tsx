'use client';

import { useEffect, useState } from 'react';
import { signOut as nextAuthSignOut, useSession as useNextAuthSession } from 'next-auth/react';
import { supabaseBrowser } from '@/lib/supabase/browser';
import { isSupabaseAuthEnabled } from '@/lib/supabase/env';

export type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AppSession {
  accessToken?: string;
  syncError?: string;
  user?: { id?: string | null; email?: string | null; name?: string | null };
}

function useSupabaseSession(): { data: AppSession | null; status: SessionStatus } {
  const enabled = isSupabaseAuthEnabled();
  const [status, setStatus] = useState<SessionStatus>(enabled ? 'loading' : 'unauthenticated');
  const [session, setSession] = useState<AppSession | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const client = supabaseBrowser();
    let active = true;

    const apply = (accessToken: string | undefined, id?: string, email?: string | null) => {
      if (!active) return;
      if (accessToken) {
        setSession({ accessToken, user: { id, email } });
        setStatus('authenticated');
      } else {
        setSession(null);
        setStatus('unauthenticated');
      }
    };

    client.auth.getSession().then(({ data }) => {
      apply(data.session?.access_token, data.session?.user.id, data.session?.user.email);
    });

    const { data: subscription } = client.auth.onAuthStateChange((_event, next) => {
      apply(next?.access_token, next?.user.id, next?.user.email);
    });

    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
  }, [enabled]);

  return { data: session, status };
}

export function useSession(): { data: AppSession | null; status: SessionStatus } {
  const next = useNextAuthSession();
  const supabase = useSupabaseSession();
  if (!isSupabaseAuthEnabled()) {
    return {
      data: (next.data as AppSession | null) ?? null,
      status: next.status,
    };
  }
  return supabase;
}

export async function signOut(options?: { callbackUrl?: string; redirect?: boolean }) {
  if (isSupabaseAuthEnabled()) {
    await supabaseBrowser().auth.signOut();
    if (options?.redirect !== false) {
      window.location.assign(options?.callbackUrl || '/login');
    }
    return;
  }
  return nextAuthSignOut(options);
}
