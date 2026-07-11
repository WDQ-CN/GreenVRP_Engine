import type {
  BackendSolverParams,
  BackendVehicleConfigItem,
  Customer,
  SolveResponse,
  VehicleSpec,
} from '@/types';
import type { ISolverRepository } from './repositories/interfaces';
import {
  buildSolveRequest,
  HttpSolverRepository,
  HttpJobStatusRepository,
} from './repositories/solverRepository';
import { logger } from './logger';

let repository: ISolverRepository | null = null;

/**
 * 设置自定义 Repository 实现（主要用于测试注入 Mock）。
 */
export function setSolverRepository(repo: ISolverRepository): void {
  repository = repo;
}

function getRepository(): ISolverRepository {
  if (!repository) {
    repository = new HttpSolverRepository();
  }
  return repository;
}

export function buildVehicleConfigMap(
  vehicleConfig: VehicleSpec[]
): Record<string, BackendVehicleConfigItem> {
  return vehicleConfig.reduce(
    (acc, vehicle) => {
      const {
        type,
        count,
        capacity,
        fixed_cost,
        fuel_consumption_per_100km,
        avg_speed_kmh,
        color,
      } = vehicle;
      acc[type] = {
        count,
        capacity,
        fixed_cost,
        fuel_per_100km: fuel_consumption_per_100km,
        speed_kmh: avg_speed_kmh,
        color,
      };
      return acc;
    },
    {} as Record<string, BackendVehicleConfigItem>
  );
}

export function buildSolverParams(params: {
  fuel_price: number;
  hourly_wage: number;
  carbon_price: number;
  late_penalty_per_min: number;
  search_time_limit: number;
  use_multi_strategy: boolean;
  use_parallel: boolean;
}): BackendSolverParams {
  return {
    fuel_price: params.fuel_price,
    hourly_wage: params.hourly_wage,
    carbon_price: params.carbon_price,
    late_penalty_per_min: params.late_penalty_per_min,
    search_time_limit: params.search_time_limit,
    use_multi_strategy: params.use_multi_strategy,
    use_parallel: params.use_parallel,
  };
}

export function normalizeCustomers(customers: Customer[]): Customer[] {
  const depot = customers.find((c) => c.is_depot || c.id === 0);
  const others = customers.filter((c) => c !== depot);
  return depot ? [depot, ...others] : customers;
}

const logPrefix = '[Solver]';

export async function solveSync(
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
  }
): Promise<SolveResponse> {
  logger.debug(`${logPrefix} solveSync 委托: customers=%d`, customers.length);
  const request = buildSolveRequest(customers, vehicleConfig, params);
  return getRepository().solveSync(request);
}

export async function solveAsync(
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
): Promise<{ job_id: string; status: string; message: string }> {
  logger.debug(
    `${logPrefix} solveAsync 委托: customers=%d, callback=%s`,
    customers.length,
    callbackUrl || '无'
  );
  const request = buildSolveRequest(
    customers,
    vehicleConfig,
    params,
    callbackUrl
  );
  return getRepository().solveAsync(request);
}

export async function getJobStatus(jobId: string): Promise<SolveResponse> {
  logger.debug(`${logPrefix} getJobStatus 委托: job_id=%s`, jobId);
  return getRepository().getJobStatus(jobId);
}

export interface PollOptions {
  intervalMs?: number;
  maxAttempts?: number;
  onProgress?: (response: SolveResponse) => void;
  signal?: AbortSignal;
}

export async function pollJobStatus(
  jobId: string,
  options: PollOptions = {}
): Promise<SolveResponse> {
  logger.debug(
    `${logPrefix} pollJobStatus 委托: job_id=%s, options=%o`,
    jobId,
    options
  );
  const statusRepo = new HttpJobStatusRepository(getRepository());
  return statusRepo.pollJobStatus(jobId, options);
}
