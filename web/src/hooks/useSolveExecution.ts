import axios from 'axios';
import { useCallback, useRef, useState } from 'react';
import { solveAsync, solveSync, pollJobStatus } from '@/lib/solver';
import { logger } from '@/lib/logger';
import { SolverRepositoryError } from '@/lib/repositories/solverRepository';
import type {
  Customer,
  SolverParams,
  SolveResponse,
  VehicleSpec,
} from '@/types';
import { useSolveValidation } from './useSolveValidation';

const logPrefix = '[useSolveExecution]';

function isCancellationError(error: unknown): boolean {
  if (axios.isCancel(error)) return true;
  if (error instanceof Error && error.name === 'AbortError') return true;
  if (error instanceof Error && error.name === 'CanceledError') return true;
  if (
    error instanceof SolverRepositoryError &&
    error.message.includes('已取消')
  )
    return true;
  return false;
}

interface UseSolveExecutionOptions {
  onComplete?: (response: SolveResponse) => void;
}

/**
 * 求解执行 Hook
 *
 * 封装求解任务的完整生命周期：验证 → 执行 → 进度 → 完成/错误。
 * 不依赖 Zustand store，通过参数传递数据。
 */
export function useSolveExecution(options?: UseSolveExecutionOptions) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { validate } = useSolveValidation();
  const { onComplete } = options ?? {};

  const handleSolve = useCallback(
    async (
      customers: Customer[],
      vehicleConfig: VehicleSpec[],
      params: SolverParams,
      useAsync: boolean
    ) => {
      // 验证
      const validationError = validate(customers);
      if (validationError) {
        logger.warn(`${logPrefix} 验证失败: %s`, validationError);
        setError(validationError);
        return;
      }

      logger.debug(
        `${logPrefix} 求解开始: customers=%d, useAsync=%s`,
        customers.length,
        useAsync
      );

      setLoading(true);
      setError(null);
      setProgress(null);
      abortRef.current = new AbortController();

      try {
        let response: SolveResponse;
        if (useAsync) {
          logger.debug(`${logPrefix} 使用异步模式`);
          const job = await solveAsync(customers, vehicleConfig, params);
          logger.debug(`${logPrefix} 异步任务已创建: job_id=%s`, job.job_id);
          response = await pollJobStatus(job.job_id, {
            onProgress: (res) => {
              if (typeof res.progress === 'number') {
                setProgress(res.progress);
              } else if (res.status === 'processing') {
                setProgress((prev) =>
                  prev === null ? 10 : Math.min(prev + 5, 90)
                );
              }
            },
            signal: abortRef.current.signal,
          });
        } else {
          logger.debug(`${logPrefix} 使用同步模式`);
          response = await solveSync(customers, vehicleConfig, params);
        }

        logger.debug(`${logPrefix} 求解完成: status=%s`, response.status);
        onComplete?.(response);
      } catch (err) {
        if (isCancellationError(err)) {
          logger.warn(`${logPrefix} 求解已取消`);
          setError('求解已取消');
        } else {
          const message =
            err instanceof Error
              ? err.message
              : '求解失败，请检查网络或 API 配置';
          logger.error(`${logPrefix} 求解失败: %s`, message);
          setError(message);
        }
      } finally {
        setLoading(false);
        setProgress(null);
        abortRef.current = null;
        logger.debug(`${logPrefix} 状态已重置`);
      }
    },
    [onComplete, validate]
  );

  const handleCancel = useCallback(() => {
    logger.debug(`${logPrefix} 用户取消求解`);
    abortRef.current?.abort();
  }, []);

  const clearError = useCallback(() => {
    logger.debug(`${logPrefix} 清除错误`);
    setError(null);
  }, []);

  return {
    loading,
    error,
    progress,
    handleSolve,
    handleCancel,
    clearError,
  } as const;
}
