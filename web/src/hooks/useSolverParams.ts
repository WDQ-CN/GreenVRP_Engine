import { useCallback } from 'react';
import { useSolverStore } from '@/stores/solverStore';
import type { SolverParams } from '@/types';

/**
 * 求解参数管理 Hook
 *
 * 封装对求解参数的访问和操作，组件不直接访问 Zustand store。
 */
export function useSolverParams() {
  const params = useSolverStore((s) => s.params);
  const setParams = useSolverStore((s) => s.setParams);

  return {
    params,
    setParams: useCallback(
      (p: Partial<SolverParams>) => setParams(p),
      [setParams]
    ),
  } as const;
}
