"""
API 性能基准测试脚本

启动本地 uvicorn 服务，对关键端点进行压力测试，输出 P50/P95/P99 响应时间与吞吐量。

环境变量：
    GREENVRP_API_KEY：测试用 API Key（默认 benchmark-key）
    GREENVRP_API_PORT：服务端口（默认 8000）
"""

import json
import logging
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

API_KEY = os.getenv("GREENVRP_API_KEY", "benchmark-key")
API_PORT = int(os.getenv("GREENVRP_API_PORT", "8000"))
BASE_URL = f"http://127.0.0.1:{API_PORT}"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def _make_customers(n: int = 20, seed: int = 42) -> list[dict]:
    import numpy as np

    rng = np.random.default_rng(seed)
    base_lat, base_lon = 31.2304, 121.4737
    customers = [
        {
            "id": 0,
            "name": "仓库",
            "lat": base_lat,
            "lon": base_lon,
            "demand": 0,
            "service_time_min": 0,
            "tw_earliest": 0,
            "tw_latest": 1440,
        }
    ]
    for i in range(1, n + 1):
        customers.append(
            {
                "id": i,
                "name": f"客户_{i}",
                "lat": float(base_lat + rng.uniform(-0.5, 0.5)),
                "lon": float(base_lon + rng.uniform(-0.5, 0.5)),
                "demand": int(rng.integers(1, 100)),
                "service_time_min": int(rng.integers(5, 30)),
                "tw_earliest": int(rng.integers(0, 480)),
                "tw_latest": int(rng.integers(540, 1080)),
            }
        )
    return customers


def _ensure_time_windows(customers: list[dict]) -> list[dict]:
    for c in customers:
        if c["tw_latest"] < c["tw_earliest"] + 60:
            c["tw_latest"] = c["tw_earliest"] + 60
    return customers


def _wait_for_server(client: httpx.Client, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = client.get(f"{BASE_URL}/api/v1/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("API 服务启动超时")


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def _bench_endpoint(
    client: httpx.Client,
    name: str,
    method: str,
    path: str,
    json_body: dict | None = None,
    iterations: int = 20,
) -> dict:
    latencies = []
    errors = 0
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            if method == "GET":
                r = client.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=30.0)
            else:
                r = client.post(
                    f"{BASE_URL}{path}",
                    headers=HEADERS,
                    json=json_body,
                    timeout=60.0,
                )
            if r.status_code >= 400:
                errors += 1
        except Exception:
            errors += 1
        finally:
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)
    return {
        "name": name,
        "iterations": iterations,
        "errors": errors,
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
    }


def run(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or (Path(__file__).parent / "results")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["GREENVRP_API_KEY"] = API_KEY
    # 基准测试需要连续调用 /solve，关闭限流避免 429 干扰
    env["GREENVRP_RATE_LIMIT_DISABLED"] = "true"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(API_PORT),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    results: dict[str, list[dict] | dict] = {"endpoints": []}
    client = httpx.Client()

    try:
        _wait_for_server(client)
        logger.info("API 服务已启动: %s", BASE_URL)

        # 健康检查基线
        results["endpoints"].append(
            _bench_endpoint(client, "health", "GET", "/api/v1/health", iterations=50)
        )

        # 场景创建（少量客户）
        customers = _ensure_time_windows(_make_customers(10))
        scenario_payload = {
            "name": "benchmark-scenario",
            "description": "用于性能测试的场景",
            "customers": customers,
        }
        create_result = _bench_endpoint(
            client,
            "create_scenario",
            "POST",
            "/api/v1/scenarios",
            json_body=scenario_payload,
            iterations=20,
        )
        results["endpoints"].append(create_result)

        # 场景列表
        results["endpoints"].append(
            _bench_endpoint(client, "list_scenarios", "GET", "/api/v1/scenarios", iterations=30)
        )

        # 同步求解（20 客户，短时间限制）
        solve_customers = _ensure_time_windows(_make_customers(20))
        solve_payload = {
            "customers": solve_customers,
            "params": {
                "search_time_limit": 5,
                "use_multi_strategy": False,
                "use_parallel": False,
            },
        }
        # /solve 限流 10/min，iterations 控制在 5 以内
        results["endpoints"].append(
            _bench_endpoint(
                client,
                "solve_sync",
                "POST",
                "/api/v1/solve",
                json_body=solve_payload,
                iterations=5,
            )
        )

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        client.close()

    output_file = output_dir / "api_benchmark.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("API 基准结果已保存: %s", output_file)
    for ep in results["endpoints"]:
        logger.info(
            "%20s p50=%8.2fms p95=%8.2fms errors=%s",
            ep["name"],
            ep["p50_ms"],
            ep["p95_ms"],
            ep["errors"],
        )
    return results


if __name__ == "__main__":
    run()
