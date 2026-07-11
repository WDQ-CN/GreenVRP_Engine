import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  HttpSolverRepository,
  HttpJobStatusRepository,
} from '../solverRepository';
import type { ISolverRepository } from '../interfaces';
import type { SolveRequest } from '@/types';

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('HttpSolverRepository', () => {
  let repo: ISolverRepository;

  beforeEach(() => {
    vi.clearAllMocks();
    repo = new HttpSolverRepository();
  });

  it('implements ISolverRepository', () => {
    expect(repo).toBeDefined();
    expect(typeof repo.solveSync).toBe('function');
    expect(typeof repo.solveAsync).toBe('function');
    expect(typeof repo.getJobStatus).toBe('function');
  });

  it('solveSync calls api.post with correct payload', async () => {
    const { api } = await import('@/lib/api');
    vi.mocked(api.post).mockResolvedValue({
      data: {
        job_id: 'sync',
        status: 'completed',
        solution: {
          routes: [],
          total_distance: 0,
          vehicles_used: {},
          total_late_minutes: 0,
          solution_status: 'OPTIMAL',
          solve_time_seconds: 1,
        },
        cost_result: { total_cost: 0 },
      },
    });

    const request: SolveRequest = {
      customers: [
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
      ],
    };

    const result = await repo.solveSync(request);

    expect(api.post).toHaveBeenCalledWith(
      '/solve',
      expect.objectContaining({
        customers: expect.any(Array),
      })
    );
    expect(result.status).toBe('completed');
  });

  it('solveAsync calls api.post with /solve/async', async () => {
    const { api } = await import('@/lib/api');
    vi.mocked(api.post).mockResolvedValue({
      data: { job_id: 'job-1', status: 'pending', message: '任务已创建' },
    });

    const request: SolveRequest = {
      customers: [],
      callback_url: 'https://example.com/callback',
    };

    const result = await repo.solveAsync(request);

    expect(api.post).toHaveBeenCalledWith(
      '/solve/async',
      expect.objectContaining({ callback_url: 'https://example.com/callback' })
    );
    expect(result.job_id).toBe('job-1');
  });

  it('getJobStatus calls api.get', async () => {
    const { api } = await import('@/lib/api');
    vi.mocked(api.get).mockResolvedValue({
      data: { job_id: 'job-1', status: 'processing', progress: 50 },
    });

    const result = await repo.getJobStatus('job-1');

    expect(api.get).toHaveBeenCalledWith('/jobs/job-1');
    expect(result.progress).toBe(50);
  });
});

describe('HttpJobStatusRepository', () => {
  it('implements IJobStatusRepository', () => {
    const mockRepo = new HttpSolverRepository();
    const statusRepo = new HttpJobStatusRepository(mockRepo);
    expect(typeof statusRepo.pollJobStatus).toBe('function');
  });

  it('resolves when job completes', async () => {
    const mockRepo: ISolverRepository = {
      solveSync: vi.fn(),
      solveAsync: vi.fn(),
      getJobStatus: vi.fn().mockResolvedValue({
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
        cost_result: { total_cost: 0 },
      }),
    };

    const statusRepo = new HttpJobStatusRepository(mockRepo);
    const result = await statusRepo.pollJobStatus('job-1', { intervalMs: 50 });

    expect(result.status).toBe('completed');
    expect(mockRepo.getJobStatus).toHaveBeenCalledWith('job-1');
  });

  it('polls until job completes', async () => {
    const mockRepo: ISolverRepository = {
      solveSync: vi.fn(),
      solveAsync: vi.fn(),
      getJobStatus: vi
        .fn()
        .mockResolvedValueOnce({ job_id: 'job-1', status: 'pending' })
        .mockResolvedValueOnce({ job_id: 'job-1', status: 'pending' })
        .mockResolvedValueOnce({
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
          cost_result: { total_cost: 0 },
        }),
    };

    const statusRepo = new HttpJobStatusRepository(mockRepo);
    const onProgress = vi.fn();
    const result = await statusRepo.pollJobStatus('job-1', {
      intervalMs: 50,
      onProgress,
    });

    expect(result.status).toBe('completed');
    expect(onProgress).toHaveBeenCalledTimes(3);
  });

  it('throws when job fails', async () => {
    const mockRepo: ISolverRepository = {
      solveSync: vi.fn(),
      solveAsync: vi.fn(),
      getJobStatus: vi.fn().mockResolvedValue({
        job_id: 'job-1',
        status: 'failed',
        error_message: '求解失败',
      }),
    };

    const statusRepo = new HttpJobStatusRepository(mockRepo);
    await expect(
      statusRepo.pollJobStatus('job-1', { intervalMs: 50 })
    ).rejects.toThrow('求解失败');
  });

  it('throws on abort signal', async () => {
    const mockRepo: ISolverRepository = {
      solveSync: vi.fn(),
      solveAsync: vi.fn(),
      getJobStatus: vi
        .fn()
        .mockResolvedValue({ job_id: 'job-1', status: 'pending' }),
    };

    const statusRepo = new HttpJobStatusRepository(mockRepo);
    const controller = new AbortController();
    const promise = statusRepo.pollJobStatus('job-1', {
      intervalMs: 50,
      signal: controller.signal,
    });

    controller.abort();
    await expect(promise).rejects.toThrow('求解任务已取消');
  });
});
