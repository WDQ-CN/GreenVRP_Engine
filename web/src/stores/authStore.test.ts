import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ apiKey: null, isAuthenticated: false });
  });

  it('initializes unauthenticated', () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.apiKey).toBeNull();
  });

  it('sets api key and authenticates', () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.setApiKey('test-key');
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.apiKey).toBe('test-key');
    expect(localStorage.getItem('greenvrp_api_key')).toBe('test-key');
  });

  it('clears api key', () => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.setApiKey('test-key');
      result.current.clearApiKey();
    });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.apiKey).toBeNull();
    expect(localStorage.getItem('greenvrp_api_key')).toBeNull();
  });
});
