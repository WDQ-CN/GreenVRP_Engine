import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from './api';
import {
  buildSolverParams,
  buildVehicleConfigMap,
  getJobStatus,
  normalizeCustomers,
  pollJobStatus,
} from './solver';
import type { Customer, SolveResponse, VehicleSpec } from '@/types';

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('buildVehicleConfigMap', () => {
  it('maps vehicle spec fields to backend format', () => {
    const config: VehicleSpec[] = [
      {
        type: '4.2m',
        count: 2,
        capacity: 800,
        fixed_cost: 300,
        fuel_consumption_per_100km: 12,
        avg_speed_kmh: 40,
        color: '#2563EB',
        emission_kg_per_km: 0.27,
      },
    ];

    const result = buildVehicleConfigMap(config);

    expect(result['4.2m']).toEqual({
      count: 2,
      capacity: 800,
      fixed_cost: 300,
      fuel_per_100km: 12,
      speed_kmh: 40,
      color: '#2563EB',
    });
  });
});

describe('buildSolverParams', () => {
  it('passes through solver parameters', () => {
    const params = {
      fuel_price: 7.5,
      hourly_wage: 50,
      carbon_price: 0.08,
      late_penalty_per_min: 10,
      search_time_limit: 30,
      use_multi_strategy: true,
      use_parallel: true,
    };

    expect(buildSolverParams(params)).toEqual(params);
  });
});

describe('normalizeCustomers', () => {
  it('moves depot to the front of the list', () => {
    const customers: Customer[] = [
      {
        id: 1,
        name: '客户A',
        lat: 39.9,
        lon: 116.4,
        demand: 50,
        service_time_min: 15,
        tw_earliest: 480,
        tw_latest: 720,
      },
      {
        id: 0,
        name: '仓库',
        lat: 39.91,
        lon: 116.41,
        demand: 0,
        service_time_min: 0,
        tw_earliest: 0,
        tw_latest: 1440,
        is_depot: true,
      },
    ];

    const result = normalizeCustomers(customers);

    expect(result[0].is_depot).toBe(true);
    expect(result).toHaveLength(2);
  });

  it('returns original list when no depot exists', () => {
    const customers: Customer[] = [
      {
        id: 1,
        name: '客户A',
        lat: 39.9,
        lon: 116.4,
        demand: 50,
        service_time_min: 15,
        tw_earliest: 480,
        tw_latest: 720,
      },
    ];

    expect(normalizeCustomers(customers)).toEqual(customers);
  });
});

describe('pollJobStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('resolves when job completes', async () => {
    const completed: SolveResponse = {
      job_id: 'job-1',
      status: 'completed',
      solution: {
        routes: [],
        total_distance: 0,
        vehicles_used: {},
        total_late_minutes: 0,
        solution_status: 'OPTIMAL',
        solve_time_seconds: 1,
      },
      cost_result: {
        transport_cost: 0,
        labor_cost: 0,
        fixed_cost: 0,
        penalty_cost: 0,
        carbon_cost: 0,
        total_cost: 0,
        carbon_emission_kg: 0,
        total_distance_km: 0,
        total_time_min: 0,
        driving_time_min: 0,
        service_time_min: 0,
        waiting_time_min: 0,
        cost_breakdown: {},
      },
    };

    vi.mocked(api.get).mockResolvedValue({ data: completed });

    const promise = pollJobStatus('job-1', { intervalMs: 100 });
    const result = await promise;

    expect(result.status).toBe('completed');
    expect(api.get).toHaveBeenCalledWith('/jobs/job-1');
  });

  it('polls until job completes', async () => {
    const pending: SolveResponse = {
      job_id: 'job-1',
      status: 'pending',
    };
    const completed: SolveResponse = {
      job_id: 'job-1',
      status: 'completed',
      solution: {
        routes: [],
        total_distance: 0,
        vehicles_used: {},
        total_late_minutes: 0,
        solution_status: 'OPTIMAL',
        solve_time_seconds: 1,
      },
      cost_result: {
        transport_cost: 0,
        labor_cost: 0,
        fixed_cost: 0,
        penalty_cost: 0,
        carbon_cost: 0,
        total_cost: 0,
        carbon_emission_kg: 0,
        total_distance_km: 0,
        total_time_min: 0,
        driving_time_min: 0,
        service_time_min: 0,
        waiting_time_min: 0,
        cost_breakdown: {},
      },
    };

    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: pending })
      .mockResolvedValueOnce({ data: pending })
      .mockResolvedValueOnce({ data: completed });

    const onProgress = vi.fn();
    const promise = pollJobStatus('job-1', {
      intervalMs: 100,
      onProgress,
    });

    await vi.advanceTimersByTimeAsync(250);
    const result = await promise;

    expect(result.status).toBe('completed');
    expect(onProgress).toHaveBeenCalledTimes(3);
  });

  it('throws when job fails', async () => {
    const failed: SolveResponse = {
      job_id: 'job-1',
      status: 'failed',
      error_message: '求解失败',
    };

    vi.mocked(api.get).mockResolvedValue({ data: failed });

    await expect(pollJobStatus('job-1', { intervalMs: 100 })).rejects.toThrow(
      '求解失败'
    );
  });

  it('throws on abort signal', async () => {
    const pending: SolveResponse = {
      job_id: 'job-1',
      status: 'pending',
    };

    vi.mocked(api.get).mockResolvedValue({ data: pending });

    const controller = new AbortController();
    const promise = pollJobStatus('job-1', {
      intervalMs: 100,
      signal: controller.signal,
    });

    controller.abort();

    await expect(promise).rejects.toThrow('求解任务已取消');
  });
});

describe('getJobStatus', () => {
  it('fetches job status from api', async () => {
    const response: SolveResponse = {
      job_id: 'job-1',
      status: 'processing',
      progress: 50,
    };

    vi.mocked(api.get).mockResolvedValue({ data: response });

    const result = await getJobStatus('job-1');

    expect(result).toEqual(response);
    expect(api.get).toHaveBeenCalledWith('/jobs/job-1');
  });
});
