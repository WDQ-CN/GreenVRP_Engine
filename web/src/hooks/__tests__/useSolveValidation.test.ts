import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Customer } from '@/types';

describe('useSolveValidation', () => {
  it('returns error when no depot exists', async () => {
    const { useSolveValidation } = await import('../useSolveValidation');
    const { result } = renderHook(() => useSolveValidation());

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

    const error = result.current.validate(customers);
    expect(error).toBe('请至少设置一个仓库节点（is_depot=true）');
  });

  it('returns error when only depot exists', async () => {
    const { useSolveValidation } = await import('../useSolveValidation');
    const { result } = renderHook(() => useSolveValidation());

    const customers: Customer[] = [
      {
        id: 0,
        name: '仓库',
        lat: 39.9,
        lon: 116.4,
        demand: 0,
        service_time_min: 0,
        tw_earliest: 0,
        tw_latest: 1440,
        is_depot: true,
      },
    ];

    const error = result.current.validate(customers);
    expect(error).toBe('请至少添加一个仓库和一个客户');
  });

  it('returns null for valid data', async () => {
    const { useSolveValidation } = await import('../useSolveValidation');
    const { result } = renderHook(() => useSolveValidation());

    const customers: Customer[] = [
      {
        id: 0,
        name: '仓库',
        lat: 39.9,
        lon: 116.4,
        demand: 0,
        service_time_min: 0,
        tw_earliest: 0,
        tw_latest: 1440,
        is_depot: true,
      },
      {
        id: 1,
        name: '客户A',
        lat: 39.91,
        lon: 116.41,
        demand: 50,
        service_time_min: 15,
        tw_earliest: 480,
        tw_latest: 720,
      },
    ];

    const error = result.current.validate(customers);
    expect(error).toBeNull();
  });
});
