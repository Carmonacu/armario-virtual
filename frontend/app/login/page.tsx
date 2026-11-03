'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { getProviders, getSession, signIn } from 'next-auth/react';
import { useSession } from '@/lib/session';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { API_BASE_PATH } from '@/lib/api';
import { safeCallbackUrl } from '@/lib/callback-url';
import {
  FORWARD_AUTH_ACCOUNT_CONFLICT,
  FORWARD_AUTH_SERVER_ERROR,
  FORWARD_AUTH_USERNAME_CONFLICT,
} from '@/lib/auth-errors';
import { useAuthConfig } from '@/lib/hooks/use-auth-config';
import { supabaseBrowser } from '@/lib/supabase/browser';
import {
  isSupabaseAuthEnabled,
  supabaseOAuthProviders,
  type SupabaseOAuthProvider,
} from '@/lib/supabase/env';

function oauthProviderLabel(
  provider: SupabaseOAuthProvider,
  t: (key: 'supabase.providers.google' | 'supabase.providers.github') => string
) {
  return provider === 'google' ? t('supabase.providers.google') : t('supabase.providers.github');
}

function SupabaseLogin({ getCallbackUrl }: { getCallbackUrl: () => string }) {
  const t = useTranslations('auth');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const providers = supabaseOAuthProviders();

  const redirectTo = () =>
    `${window.location.origin}/auth/callback?next=${encodeURIComponent(getCallbackUrl())}`;

  const signInWithPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setNotice(null);
    const { error: authError } = await supabaseBrowser().auth.signInWithPassword({ email, password });
    setIsLoading(false);
    if (authError) setError(t('supabase.invalidCredentials'));
  };

  const sendMagicLink = async () => {
    if (!email) return;
    setIsLoading(true);
    setError(null);
    const { error: authError } = await supabaseBrowser().auth.signInWithOtp({
      email,
      options: { emailRedirectTo: redirectTo() },
    });
    setIsLoading(false);
    if (authError) {
      setError(t('errors.default'));
      return;
    }
    setNotice(t('supabase.magicLinkSent'));
  };

  const startOAuth = async (provider: SupabaseOAuthProvider) => {
    setError(null);
    const { error: authError } = await supabaseBrowser().auth.signInWithOAuth({
      provider,
      options: { redirectTo: redirectTo() },
    });
    if (authError) setError(t('errors.default'));
  };

  return (
    <form onSubmit={signInWithPassword} className="space-y-4">
      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">{error}</div>
      )}
      {notice && <div className="rounded-md bg-primary/10 p-4 text-sm">{notice}</div>}
      <div className="space-y-2">
        <label htmlFor="supabase-email" className="block text-sm font-medium">
          {t('email')}
        </label>
        <input
          id="supabase-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <div className="space-y-2">
        <label htmlFor="supabase-password" className="block text-sm font-medium">
          {t('supabase.password')}
        </label>
        <input
          id="supabase-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-3 text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('signingIn')}
          </>
        ) : (
          t('supabase.signIn')
        )}
      </button>
      <button
        type="button"
        onClick={sendMagicLink}
        disabled={isLoading || !email}
        className="flex w-full items-center justify-center rounded-md border border-input px-4 py-3 text-sm hover:bg-accent disabled:opacity-50"
      >
        {t('supabase.magicLink')}
      </button>
      {providers.length > 0 && (
        <div className="space-y-3">
          <p className="text-center text-sm text-muted-foreground">{t('supabase.or')}</p>
          {providers.map((provider) => (
            <button
              key={provider}
              type="button"
              onClick={() => startOAuth(provider)}
              className="flex w-full items-center justify-center rounded-md border border-input px-4 py-3 text-sm hover:bg-accent"
            >
              {t('supabase.oauth', { provider: oauthProviderLabel(provider, t) })}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

function OIDCLoginButton({ getCallbackUrl }: { getCallbackUrl: () => string }) {
  const t = useTranslations('auth');

  return (
    <button
      onClick={() => signIn('oidc', { callbackUrl: getCallbackUrl() })}
      className="flex w-full items-center justify-center gap-3 rounded-md bg-primary px-4 py-3 text-primary-foreground hover:bg-primary/90 transition-colors"
    >
      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
      </svg>
      {t('title')}
    </button>
  );
}

function DevLogin({ getCallbackUrl }: { getCallbackUrl: () => string }) {
  const [email, setEmail] = useState('dev@wardrobe.local');
  const [name, setName] = useState('Dev User');
  const [isLoading, setIsLoading] = useState(false);
  const t = useTranslations('auth');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    await signIn('dev-credentials', {
      email,
      name,
      callbackUrl: getCallbackUrl(),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="rounded-md bg-yellow-500/10 border border-yellow-500/20 p-3 text-sm text-yellow-600 dark:text-yellow-400">
        {t('devMode')}
      </div>
      <div className="space-y-2">
        <label htmlFor="email" className="block text-sm font-medium">
          {t('email')}
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="dev@example.com"
        />
      </div>
      <div className="space-y-2">
        <label htmlFor="name" className="block text-sm font-medium">
          {t('displayName')}
        </label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder={t('namePlaceholder')}
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-3 text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('signingIn')}
          </>
        ) : (
          t('title')
        )}
      </button>
    </form>
  );
}

type ForwardSignInState = 'idle' | 'signingIn' | 'failed';
type ForwardFailure = 'headers' | 'server' | 'conflict' | 'usernameConflict';

const FORWARD_FAILURE_MESSAGES = {
  headers: 'forwardAuth.headersMissing',
  server: 'forwardAuth.serverError',
  conflict: 'forwardAuth.accountConflict',
  usernameConflict: 'forwardAuth.usernameConflict',
} as const;

function forwardFailureFor(errorCode: string | null | undefined): ForwardFailure {
  if (errorCode === FORWARD_AUTH_SERVER_ERROR) return 'server';
  if (errorCode === FORWARD_AUTH_ACCOUNT_CONFLICT) return 'conflict';
  if (errorCode === FORWARD_AUTH_USERNAME_CONFLICT) return 'usernameConflict';
  return 'headers';
}

// Lives in LoginContent rather than ForwardLogin so that the one-shot guard survives the
// skeleton swapping ForwardLogin out while the session reloads.
function useForwardSignIn(auto: boolean) {
  const [state, setState] = useState<ForwardSignInState>('idle');
  const [failure, setFailure] = useState<ForwardFailure | null>(null);
  const attempted = useRef(false);

  const signInThroughProxy = useCallback(async () => {
    setState('signingIn');
    // redirect: false keeps a failure on this page; a redirect would go through
    // pages.error ('/login?error=...') and lose the reason.
    const result = await signIn('forward-auth', { redirect: false });
    if (!result?.ok || result.error) {
      setFailure(forwardFailureFor(result?.error));
      setState('failed');
      return;
    }
    // Success normally ends on the redirect effect, which waits for an accessToken. A logout or
    // proxy user switch in another tab can clear the new cookie first, and the button must not
    // stay disabled then.
    const session = await getSession();
    if (!session?.accessToken) setState('idle');
  }, []);

  useEffect(() => {
    if (!auto || attempted.current) return;
    attempted.current = true;
    void signInThroughProxy();
  }, [auto, signInThroughProxy]);

  return { state, failure, signInThroughProxy };
}

function ForwardLogin({
  state,
  failure,
  loggedOut,
  onSignIn,
}: {
  state: ForwardSignInState;
  failure: ForwardFailure | null;
  loggedOut: boolean;
  onSignIn: () => void;
}) {
  const t = useTranslations('auth');

  return (
    <div className="space-y-4">
      {failure && state !== 'signingIn' && (
        <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">
          {t(FORWARD_FAILURE_MESSAGES[failure])}
        </div>
      )}
      {loggedOut && !failure && state === 'idle' && (
        <p className="text-center text-sm text-muted-foreground">{t('forwardAuth.signedOut')}</p>
      )}
      <button
        type="button"
        onClick={onSignIn}
        disabled={state === 'signingIn'}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-3 text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {state === 'signingIn' ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('signingIn')}
          </>
        ) : (
          t('forwardAuth.continue')
        )}
      </button>
    </div>
  );
}

function BackendError({ message }: { message: string }) {
  const t = useTranslations('auth');

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm space-y-2">
      <p className="font-medium text-destructive">{t('backendError.title')}</p>
      <p className="text-destructive/90">{message}</p>
    </div>
  );
}

function LoginContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { data: session, status } = useSession();
  const error = searchParams.get('error');
  const syncErrorParam = searchParams.get('syncError');
  const loggedOut = searchParams.get('loggedOut') === '1';
  const callbackParam = searchParams.get('callbackUrl');
  // Resolved on use rather than during render, because the page is server-rendered too and
  // the same-origin check needs window.location.
  const getCallbackUrl = useCallback(
    () => safeCallbackUrl(callbackParam, window.location.origin),
    [callbackParam]
  );
  const [backendError, setBackendError] = useState<string | null>(null);
  const t = useTranslations('auth');

  useEffect(() => {
    if (status === 'authenticated' && session?.accessToken) {
      router.push(getCallbackUrl());
    }
  }, [status, session?.accessToken, getCallbackUrl, router]);

  // Check backend auth configuration on mount
  useEffect(() => {
    fetch(`${API_BASE_PATH}/auth/status`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.configured && data.error) {
          setBackendError(data.error);
        }
      })
      .catch(() => {
        setBackendError(t('backendError.description'));
      });
  }, [t]);

  const syncError = syncErrorParam || session?.syncError;

  const [providerMode, setProviderMode] = useState<'loading' | 'oidc' | 'dev' | 'unconfigured'>('loading');
  const authConfig = useAuthConfig();
  const supabaseAuth = isSupabaseAuthEnabled();

  useEffect(() => {
    if (supabaseAuth) return;
    getProviders().then((providers) => {
      if (providers?.['oidc']) {
        setProviderMode('oidc');
      } else if (providers?.['dev-credentials']) {
        setProviderMode('dev');
      } else {
        setProviderMode('unconfigured');
      }
    });
  }, [supabaseAuth]);

  const authMode = supabaseAuth
    ? 'supabase'
    : authConfig.isPending
      ? 'loading'
      : authConfig.data?.forward_auth
        ? 'forward'
        : providerMode;

  const forward = useForwardSignIn(
    authMode === 'forward' && status === 'unauthenticated' && !error && !loggedOut
  );

  if (status === 'loading' || authMode === 'loading') {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-12 bg-muted rounded-md" />
      </div>
    );
  }

  return (
    <>
      {backendError && <BackendError message={backendError} />}

      {!backendError && syncError && <BackendError message={syncError} />}

      {error && authMode !== 'forward' && !backendError && !syncError && (
        <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">
          {error === 'OAuthSignin' && t('errors.OAuthSignin')}
          {error === 'OAuthCallback' && t('errors.OAuthCallback')}
          {error === 'OAuthCreateAccount' && t('errors.OAuthCreateAccount')}
          {error === 'Callback' && t('errors.Callback')}
          {error === 'CredentialsSignin' && t('errors.CredentialsSignin')}
          {error === 'AccessDenied' && t('errors.AccessDenied')}
          {error === 'undefined' && t('errors.notConfigured')}
          {!['OAuthSignin', 'OAuthCallback', 'OAuthCreateAccount', 'Callback', 'CredentialsSignin', 'AccessDenied', 'undefined'].includes(error) && t('errors.default')}
        </div>
      )}

      <div className="space-y-4">
        {authMode === 'supabase' && <SupabaseLogin getCallbackUrl={getCallbackUrl} />}
        {authMode === 'forward' && (
          <ForwardLogin
            state={forward.state}
            failure={
              forward.state === 'failed' ? forward.failure : error ? forwardFailureFor(error) : null
            }
            loggedOut={loggedOut}
            onSignIn={forward.signInThroughProxy}
          />
        )}
        {authMode === 'oidc' && <OIDCLoginButton getCallbackUrl={getCallbackUrl} />}
        {authMode === 'dev' && <DevLogin getCallbackUrl={getCallbackUrl} />}
        {authMode === 'unconfigured' && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm space-y-2">
            <p className="font-medium text-destructive">{t('unconfigured.title')}</p>
            <p className="text-destructive/90">
              {t.rich('unconfigured.description', {
                code: (chunks) => <code className="font-mono">{chunks}</code>,
              })}
            </p>
          </div>
        )}
      </div>
    </>
  );
}

export default function LoginPage() {
  const t = useTranslations('auth');

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img src="/logo.svg" alt="Wardrowbe" className="h-16 w-16" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
          <p className="mt-2 text-muted-foreground">
            {t('subtitle')}
          </p>
        </div>

        <Suspense fallback={<div className="space-y-4 animate-pulse"><div className="h-12 bg-muted rounded-md" /></div>}>
          <LoginContent />
        </Suspense>

        <p className="text-center text-sm text-muted-foreground">
          {t('termsAgreement')}
        </p>
      </div>
    </main>
  );
}
