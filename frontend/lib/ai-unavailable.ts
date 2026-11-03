import { ApiError } from '@/lib/api';

export function isAiUnavailable(error: unknown): boolean {
  if (!(error instanceof ApiError) || !error.data || typeof error.data !== 'object') return false;
  const detail = (error.data as { detail?: unknown }).detail;
  if (!detail || typeof detail !== 'object') return false;
  return (detail as { code?: unknown }).code === 'ai_unavailable';
}
