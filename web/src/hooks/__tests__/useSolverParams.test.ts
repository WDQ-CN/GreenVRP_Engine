import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const mockParams = {
  fuel_price: 7.5,
  hourly_wage: 50,
  carbon_price: 0.08,
  late_penalty_per_min: 10,
  search_time_limit: 30,
  use_multi_strategy: true,
  use_parallel: true,
  strategy_weights: {
    min_distance: 0.25,
    min_vehicles: 0.25,
    min_cost: 0.25,
    min_emission: 0.25,
  },
};

const mockSetParams = vi.fn();

vi.mock('@/stores/solverStore', () => ({
  useSolverStore: vi.fn((selector) => {
    const state = {
      params: mockParams,
      setParams: mockSetParams,
    };
    return selector ? selector(state) : state;
  }),
}));

describe('useSolverParams', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns params from store', async () => {
    const { useSolverParams } = await import('../useSolverParams');
    const { result } = renderHook(() => useSolverParams());

    expect(result.current.params).toEqual(mockParams);
  });

  it('calls store setParams when updating partially', async () => {
    const { useSolverParams } = await import('../useSolverParams');
    const { result } = renderHook(() => useSolverParams());

    const partialUpdate = { fuel_price: 8.0 };
    result.current.setParams(partialUpdate);

    expect(mockSetParams).toHaveBeenCalledTimes(1);
    expect(mockSetParams).toHaveBeenCalledWith(partialUpdate);
  });
});
