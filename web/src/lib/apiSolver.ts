import { buildBaseline } from "./demoSolver"
import { ROUTE_PALETTE } from "./data"
import type {
  ApiConnection,
  CostResult,
  Customer,
  SolveOutcome,
  SolveSolution,
  SolverSettings,
  VehicleConfigMap,
} from "./types"

interface SolveResponse {
  solution: SolveSolution
  cost_result: CostResult
}

function normalizeBase(base: string): string {
  return base.trim().replace(/\/+$/, "")
}

async function request(
  connection: ApiConnection,
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(`${normalizeBase(connection.apiBase)}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": connection.apiKey,
        ...init.headers,
      },
    })
  } finally {
    window.clearTimeout(timer)
  }
}

function describeFailure(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "请求超时。请检查 API 服务是否在运行，或延长求解时间。"
  }
  if (error instanceof TypeError) {
    return "无法连接引擎。请确认 FastAPI 已启动，且地址与 CORS 配置正确。"
  }
  return error instanceof Error ? error.message : "未知错误。"
}

export async function testConnection(
  connection: ApiConnection,
): Promise<{ ok: boolean; message: string; latencyMs?: number }> {
  const started = performance.now()
  try {
    const response = await request(connection, "/api/v1/health", { method: "GET" }, 6000)
    const latency = Math.round(performance.now() - started)
    if (response.ok) {
      return { ok: true, message: `引擎在线 · ${latency} ms`, latencyMs: latency }
    }
    if (response.status === 401) {
      return { ok: false, message: "API Key 无效，请检查 X-API-Key。" }
    }
    return { ok: false, message: `引擎响应异常（HTTP ${response.status}）。` }
  } catch (error) {
    return { ok: false, message: describeFailure(error) }
  }
}

export async function solveViaApi(
  customers: Customer[],
  vehicles: VehicleConfigMap,
  settings: SolverSettings,
  connection: ApiConnection,
): Promise<SolveOutcome> {
  // 后端会从“前成本最优”和“ALNS 探针最优”两个首版解各跑一遍完整精修，
  // 最后再做 CP-SAT 配对精确重排，预留充足超时。
  const timeoutMs = (settings.search_time_limit * 35 + 420) * 1000
  try {
    const response = await request(
      connection,
      "/api/v1/solve",
      {
        method: "POST",
        body: JSON.stringify({
          customers,
          vehicle_config: Object.fromEntries(
            Object.entries(vehicles).map(([type, spec]) => [
              type,
              {
                capacity: spec.capacity,
                fixed_cost: spec.fixed_cost,
                fuel_per_100km: spec.fuel_per_100km,
                speed_kmh: spec.speed_kmh,
                count: spec.count,
                color: spec.color,
              },
            ]),
          ),
          params: { ...settings },
          scenario_name: "GreenVRP Web Console",
        }),
      },
      timeoutMs,
    )

    if (!response.ok) {
      let detail = `HTTP ${response.status}`
      try {
        const payload = (await response.json()) as { detail?: string }
        if (payload.detail) detail = payload.detail
      } catch {
        /* keep status text */
      }
      if (response.status === 401) detail = "API Key 无效，请检查连接设置。"
      throw new Error(`求解失败：${detail}`)
    }

    const payload = (await response.json()) as SolveResponse
    if (!payload.solution || !payload.cost_result) {
      throw new Error("引擎返回了空结果，请检查后端日志。")
    }

    const solution: SolveSolution = {
      ...payload.solution,
      routes: (payload.solution.routes ?? []).map((route, index) => ({
        ...route,
        vehicle_color:
          vehicles[route.vehicle_type]?.color ||
          ROUTE_PALETTE[index % ROUTE_PALETTE.length],
      })),
    }

    return {
      solution,
      cost: payload.cost_result,
      customers,
      baseline: buildBaseline(customers, solution.routes, vehicles),
      source: "api",
      solvedAt: new Date().toISOString(),
      note: "FastAPI · OR-Tools 多策略求解",
    }
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("求解失败")) throw error
    throw new Error(describeFailure(error))
  }
}
