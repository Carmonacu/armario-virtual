import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api';
import { isAiUnavailable } from '@/lib/ai-unavailable';

describe('isAiUnavailable', () => {
  it('recognises the prepared-outfit fallback code', () => {
    const error = new ApiError('down', 503, { detail: { code: 'ai_unavailable' } });
    expect(isAiUnavailable(error)).toBe(true);
  });

  it('ignores other failures', () => {
    expect(isAiUnavailable(new ApiError('no', 400, { detail: 'Not enough items' }))).toBe(false);
    expect(isAiUnavailable(new Error('network'))).toBe(false);
  });
});
