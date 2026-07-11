import axios from 'axios';

import { api } from '@/lib/api';
import { logger } from '@/lib/logger';
import { toast } from '@/lib/toast';
import {
  buildVehicleConfigMap,
  buildSolverParams,
  normalizeCustomers,
} from '@/lib/solver';
import type {
  Customer,
  SolveRequest,
  SolveResponse,
  VehicleSpec,
} from '@/types';
import type { ISolverRepository, IJobStatusRepository } from './interfaces';

const prefix = '[SolverRepo]';

/** Repository 层业务错误，携带操作上下文便于上层分类处理。 */
export class SolverRepositoryError extends Error {
  operation: 'solveSync' | 'solveAsync' | 'getJobStatus' | 'pollJobStatus';

  constructor(
    message: string,
    operation: 'solveSync' | 'solveAsync' | 'getJobStatus' | 'pollJobStatus'
  ) {
    super(message);
    this.name = 'SolverRepositoryError';
    this.operation = operation;
  }
}

function isCancelError(error: unknown): boolean {
  return (
    axios.isCancel(error) ||
    (error instanceof Error && error.name === 'CanceledError')
  );
}

export class HttpSolverRepository implements ISolverRepository {
  async solveSync(request: SolveRequest): Promise<SolveResponse> {
    const customerCount = request.customers?.length ?? 0;
    logger.debug(
      `${prefix} solveSync 请求: customers=${customerCount}, vehicleConfig=%s, params=%s`,
      request.vehicle_config ? '有' : '无',
      request.params ? '有' : '无'
    );

    const payload = this.buildPayload(request);
    const startTime = performance.now();
    try {
      const { data } = await api.post<SolveResponse>('/solve', payload);
      const elapsed = (performance.now() - startTime).toFixed(0);

      logger.debug(
        `${prefix} solveSync 完成: status=%s, elapsed=%sms`,
        data.status,
        elapsed
      );
      return data;
    } catch (error) {
      if (isCancelError(error)) throw error;
      const message = error instanceof Error ? error.message : '同步求解失败';
      logger.error(`${prefix} solveSync 失败: %s`, message);
      throw new SolverRepositoryError(`同步求解失败: ${message}`, 'solveSync');
    }
  }

  async solveAsync(request: SolveRequest): Promise<{
    job_id: string;
    status: string;
    message: string;
  }> {
    const customerCount = request.customers?.length ?? 0;
    logger.debug(
      `${prefix} solveAsync 请求: customers=%d, callback=%s`,
      customerCount,
      request.callback_url || '无'
    );

    const payload = this.buildPayload(request);
    try {
      const { data } = await api.post<{
        job_id: string;
        status: string;
        message: string;
      }>('/solve/async', payload);

      logger.debug(
        `${prefix} solveAsync 响应: job_id=%s, status=%s`,
        data.job_id,
        data.status
      );
      return data;
    } catch (error) {
      if (isCancelError(error)) throw error;
      const message =
        error instanceof Error ? error.message : '异步任务创建失败';
      logger.error(`${prefix} solveAsync 失败: %s`, message);
      throw new SolverRepositoryError(
        `异步任务创建失败: ${message}`,
        'solveAsync'
      );
    }
  }

  async getJobStatus(jobId: string): Promise<SolveResponse> {
    logger.debug(`${prefix} getJobStatus: job_id=%s`, jobId);
    try {
      const { data } = await api.get<SolveResponse>(`/jobs/${jobId}`);
      logger.debug(
        `${prefix} getJobStatus 响应: job_id=%s, status=%s`,
        jobId,
        data.status
      );
      return data;
    } catch (error) {
      if (isCancelError(error)) throw error;
      const message =
        error instanceof Error ? error.message : '查询任务状态失败';
      logger.error(
        `${prefix} getJobStatus 失败: job_id=%s, %s`,
        jobId,
        message
      );
      throw new SolverRepositoryError(
        `查询任务状态失败: ${message}`,
        'getJobStatus'
      );
    }
  }

  private buildPayload(request: SolveRequest): Record<string, unknown> {
    const payload: Record<string, unknown> = {
      customers: normalizeCustomers(request.customers),
    };
    if (request.vehicle_config) {
      payload.vehicle_config = request.vehicle_config;
    }
    if (request.params) {
      payload.params = request.params;
    }
    if (request.callback_url) {
      payload.callback_url = request.callback_url;
    }
    return payload;
  }
}

/** 构建兼容旧版 solveSync/solveAsync 调用的 SolveRequest。 */
export function buildSolveRequest(
  customers: Customer[],
  vehicleConfig: VehicleSpec[],
  params: {
    fuel_price: number;
    hourly_wage: number;
    carbon_price: number;
    late_penalty_per_min: number;
    search_time_limit: number;
    use_multi_strategy: boolean;
    use_parallel: boolean;
  },
  callbackUrl?: string
): SolveRequest {
  return {
    customers,
    vehicle_config: buildVehicleConfigMap(vehicleConfig),
    params: buildSolverParams(params),
    callback_url: callbackUrl,
  };
}

export class HttpJobStatusRepository implements IJobStatusRepository {
  #repository: ISolverRepository;

  constructor(repository: ISolverRepository) {
    this.#repository = repository;
  }

  async pollJobStatus(
    jobId: string,
    options: {
      intervalMs?: number;
      maxAttempts?: number;
      onProgress?: (response: SolveResponse) => void;
      signal?: AbortSignal;
    } = {}
  ): Promise<SolveResponse> {
    const {
      intervalMs = 1500,
      maxAttempts = 120,
      onProgress,
      signal,
    } = options;

    logger.debug(
      `${prefix} pollJobStatus 开始: job_id=%s, interval=%dms, maxAttempts=%d`,
      jobId,
      intervalMs,
      maxAttempts
    );

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (signal?.aborted) {
        logger.warn(`${prefix} pollJobStatus 已取消: job_id=%s`, jobId);
        const cancelError = new Error('求解任务已取消');
        cancelError.name = 'AbortError';
        throw cancelError;
      }

      const response = await this.#repository.getJobStatus(jobId);
      logger.debug(
        `${prefix} pollJobStatus 轮询 #%d: job_id=%s, status=%s`,
        attempt + 1,
        jobId,
        response.status
      );
      onProgress?.(response);

      if (response.status === 'completed') {
        logger.debug(
          `${prefix} pollJobStatus 完成: job_id=%s, attempts=%d`,
          jobId,
          attempt + 1
        );
        return response;
      }

      if (response.status === 'failed') {
        const errorMessage =
          response.error_message || response.error || '求解任务执行失败';
        logger.warn(
          `${prefix} pollJobStatus 失败: job_id=%s, error=%s`,
          jobId,
          errorMessage
        );
        toast({
          title: '求解失败',
          description: errorMessage,
          variant: 'destructive',
        });
        throw new SolverRepositoryError(errorMessage, 'pollJobStatus');
      }

      await new Promise<void>((resolve) => {
        const timer = setTimeout(resolve, intervalMs);
        signal?.addEventListener('abort', () => clearTimeout(timer), {
          once: true,
        });
      });
    }

    const timeoutMessage = '求解任务轮询超时，请稍后刷新页面查看结果';
    logger.error(`${prefix} pollJobStatus 超时: job_id=%s`, jobId);
    toast({
      title: '求解超时',
      description: timeoutMessage,
      variant: 'destructive',
    });
    throw new SolverRepositoryError(timeoutMessage, 'pollJobStatus');
  }
}
