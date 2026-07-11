import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const mockVehicleConfig = [
  {
    type: '4.2m',
    count: 5,
    capacity: 800,
    fixed_cost: 300,
    fuel_consumption_per_100km: 12,
    avg_speed_kmh: 40,
    color: '#2563EB',
    emission_kg_per_km: 0.27,
  },
  {
    type: '7.6m',
    count: 3,
    capacity: 1500,
    fixed_cost: 500,
    fuel_consumption_per_100km: 18,
    avg_speed_kmh: 50,
    color: '#16A34A',
    emission_kg_per_km: 0.4,
  },
];

vi.mock('@/stores/solverStore', () => ({
  useSolverStore: vi.fn((selector) => {
    const state = {
      vehicleConfig: mockVehicleConfig,
      setVehicleConfig: vi.fn(),
    };
    return selector ? selector(state) : state;
  }),
}));

describe('useVehicleConfig', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns vehicleConfig from store', async () => {
    const { useVehicleConfig } = await import('../useVehicleConfig');
    const { result } = renderHook(() => useVehicleConfig());

    expect(result.current.vehicleConfig).toEqual(mockVehicleConfig);
    expect(result.current.vehicleCount).toBe(8);
  });

  it('returns setter functions', async () => {
    const { useVehicleConfig } = await import('../useVehicleConfig');
    const { result } = renderHook(() => useVehicleConfig());

    expect(typeof result.current.setVehicleConfig).toBe('function');
  });
});
