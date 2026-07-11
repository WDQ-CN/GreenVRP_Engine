import type { SolveRequest, SolveResponse } from '@/types';

export interface ISolverRepository {
  solveSync(request: SolveRequest): Promise<SolveResponse>;
  solveAsync(request: SolveRequest): Promise<{
    job_id: string;
    status: string;
    message: string;
  }>;
  getJobStatus(jobId: string): Promise<SolveResponse>;
}

export interface IJobStatusRepository {
  pollJobStatus(
    jobId: string,
    options?: {
      intervalMs?: number;
      maxAttempts?: number;
      onProgress?: (response: SolveResponse) => void;
      signal?: AbortSignal;
    }
  ): Promise<SolveResponse>;
}
