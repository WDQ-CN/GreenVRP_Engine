import { useCallback } from 'react';
import { useSolverStore } from '@/stores/solverStore';
import type { SolveResponse } from '@/types';

/**
 * 求解结果管理 Hook
 *
 * 封装对求解结果的访问和操作，组件不直接访问 Zustand store。
 */
export function useSolver() {
  const currentSolution = useSolverStore((s) => s.currentSolution);
  const setCurrentSolution = useSolverStore((s) => s.setCurrentSolution);
  const comparisonResults = useSolverStore((s) => s.comparisonResults);
  const addComparisonResult = useSolverStore((s) => s.addComparisonResult);
  const removeComparisonResult = useSolverStore(
    (s) => s.removeComparisonResult
  );
  const clearComparisonResults = useSolverStore(
    (s) => s.clearComparisonResults
  );

  const hasSolution = currentSolution !== null;

  return {
    currentSolution,
    setCurrentSolution: useCallback(
      (solution: SolveResponse | null) => setCurrentSolution(solution),
      [setCurrentSolution]
    ),
    comparisonResults,
    addComparisonResult: useCallback(
      (solution: SolveResponse) => addComparisonResult(solution),
      [addComparisonResult]
    ),
    removeComparisonResult: useCallback(
      (index: number) => removeComparisonResult(index),
      [removeComparisonResult]
    ),
    clearComparisonResults: useCallback(
      () => clearComparisonResults(),
      [clearComparisonResults]
    ),
    hasSolution,
  } as const;
}
