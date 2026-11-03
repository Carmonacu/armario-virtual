import { DEFAULT_LOCALE as GENERATED_DEFAULT_LOCALE, SUPPORTED_LOCALES } from '@/lib/generated/locales';

export { SUPPORTED_LOCALES };

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: SupportedLocale = GENERATED_DEFAULT_LOCALE;

export const LOCALE_COOKIE = 'NEXT_LOCALE';

export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

// Keyed by SupportedLocale so tsc fails when a code in backend/app/data/locales.json has no entry.
export const LOCALE_METADATA: Record<SupportedLocale, { name: string; nativeName: string; dir: 'ltr' | 'rtl' }> = {
  es: { name: 'Spanish (Spain)', nativeName: 'Español (España)', dir: 'ltr' },
  en: { name: 'English', nativeName: 'English', dir: 'ltr' },
  'zh-CN': { name: 'Chinese (Simplified)', nativeName: '中文简体', dir: 'ltr' },
  'zh-TW': { name: 'Chinese (Traditional)', nativeName: '中文繁體', dir: 'ltr' },
  ko: { name: 'Korean', nativeName: '한국어', dir: 'ltr' },
  ja: { name: 'Japanese', nativeName: '日本語', dir: 'ltr' },
  fr: { name: 'French', nativeName: 'Français', dir: 'ltr' },
  de: { name: 'German', nativeName: 'Deutsch', dir: 'ltr' },
  it: { name: 'Italian', nativeName: 'Italiano', dir: 'ltr' },
};

export const NAMESPACES = [
  'common',
  'nav',
  'auth',
  'onboarding',
  'dashboard',
  'wardrobe',
  'suggest',
  'history',
  'settings',
  'family',
  'notifications',
  'analytics',
  'learning',
  'pairings',
  'outfits',
  'constants',
  'errors',
] as const;

export type Namespace = (typeof NAMESPACES)[number];

export function isValidLocale(locale: string | undefined | null): locale is SupportedLocale {
  return !!locale && (SUPPORTED_LOCALES as readonly string[]).includes(locale);
}

// The last NEXT_LOCALE wins because that is the one the server's cookie parser keeps.
export function readLocaleCookie(): SupportedLocale | undefined {
  const prefix = `${LOCALE_COOKIE}=`;
  const value = document.cookie
    .split('; ')
    .filter((part) => part.startsWith(prefix))
    .pop()
    ?.slice(prefix.length);
  return isValidLocale(value) ? value : undefined;
}

/** The catalog a missing key falls back to. Independent of DEFAULT_LOCALE, which this fork sets to Spanish. */
export const SOURCE_LOCALE = 'en' as const satisfies SupportedLocale;

/** Maps a browser language tag onto a supported locale, or undefined when the tag names none.
 *  Exact match first, then the base language, so `de-AT` resolves to `de`, `es-ES` to `es`
 *  and `zh-HK` to `zh-TW`. */
export function matchSupportedLocale(candidate: string | undefined | null): SupportedLocale | undefined {
  if (!candidate) return undefined;
  if (isValidLocale(candidate)) return candidate;

  const lower = candidate.toLowerCase();
  const exact = SUPPORTED_LOCALES.find((l) => l.toLowerCase() === lower);
  if (exact) return exact;

  if (lower.startsWith('zh')) {
    return /hant|tw|hk|mo/.test(lower) ? 'zh-TW' : 'zh-CN';
  }

  const base = lower.split('-')[0];
  return SUPPORTED_LOCALES.find((l) => l.toLowerCase().split('-')[0] === base);
}

/** Maps a browser Accept-Language tag onto a supported locale, using the fork default when nothing matches. */
export function resolveLocale(candidate: string | undefined | null): SupportedLocale {
  return matchSupportedLocale(candidate) ?? DEFAULT_LOCALE;
}
