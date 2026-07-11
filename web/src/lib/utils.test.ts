import { describe, expect, it } from 'vitest';

import { cn } from './utils';

describe('cn utility', () => {
  it('merges tailwind classes correctly', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('handles conditional classes', () => {
    const isLarge = false;
    expect(cn('text-base', isLarge && 'text-lg', 'font-medium')).toBe(
      'text-base font-medium'
    );
  });
});
