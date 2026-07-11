import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const mockCustomers = [
  {
    id: 0,
    name: '仓库',
    lat: 39.9042,
    lon: 116.4074,
    demand: 0,
    service_time_min: 0,
    tw_earliest: 0,
    tw_latest: 1440,
    is_depot: true,
  },
  {
    id: 1,
    name: '客户A',
    lat: 39.9142,
    lon: 116.4174,
    demand: 50,
    service_time_min: 15,
    tw_earliest: 480,
    tw_latest: 720,
  },
];

import type { SolverState } from '@/stores/solverStore';

const createMockState = (
  customersOverride?: typeof mockCustomers
): SolverState => ({
  customers: customersOverride ?? mockCustomers,
  params: {} as SolverState['params'],
  vehicleConfig: [],
  currentSolution: null,
  comparisonResults: [],
  setCustomers: vi.fn(),
  setParams: vi.fn(),
  setVehicleConfig: vi.fn(),
  setCurrentSolution: vi.fn(),
  addComparisonResult: vi.fn(),
  removeComparisonResult: vi.fn(),
  clearComparisonResults: vi.fn(),
  loadSampleData: vi.fn(),
});

vi.mock('@/stores/solverStore', () => ({
  useSolverStore: vi.fn((selector) => {
    const state = createMockState();
    return selector ? selector(state) : state;
  }),
}));

describe('useCustomers', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns customers from store', async () => {
    const { useCustomers } = await import('../useCustomers');
    const { result } = renderHook(() => useCustomers());

    expect(result.current.customers).toEqual(mockCustomers);
    expect(result.current.hasDepot).toBe(true);
    expect(result.current.customerCount).toBe(1);
    expect(result.current.totalDemand).toBe(50);
  });

  it('returns setCustomers function', async () => {
    const { useCustomers } = await import('../useCustomers');
    const { result } = renderHook(() => useCustomers());

    expect(typeof result.current.setCustomers).toBe('function');
  });

  it('returns loadSampleData function', async () => {
    const { useCustomers } = await import('../useCustomers');
    const { result } = renderHook(() => useCustomers());

    expect(typeof result.current.loadSampleData).toBe('function');
  });

  it('reports no depot when missing', async () => {
    vi.mocked(
      (await import('@/stores/solverStore')).useSolverStore
    ).mockImplementation((selector) => {
      const state = {
        ...createMockState(),
        customers: [{ ...mockCustomers[1] }],
      };
      return selector ? selector(state) : state;
    });

    const { useCustomers } = await import('../useCustomers');
    const { result } = renderHook(() => useCustomers());

    expect(result.current.hasDepot).toBe(false);
    expect(result.current.customerCount).toBe(1);
  });
});
