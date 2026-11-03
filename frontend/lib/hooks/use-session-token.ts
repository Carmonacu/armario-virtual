'use client';

import { useSession, type AppSession } from '@/lib/session';
import { setAccessToken } from '@/lib/api';

export function applySessionToken(session: AppSession | null | undefined) {
  if (session?.accessToken) {
    setAccessToken(session.accessToken);
  }
}

export function useSetTokenIfAvailable() {
  const { data: session } = useSession();
  applySessionToken(session);
}
