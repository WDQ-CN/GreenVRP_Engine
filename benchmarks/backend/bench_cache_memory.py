"""缓存拷贝策略内存与耗时基准测试。

对比 deepcopy / model_copy(deep=True) 与 JSON 序列化/反序列化 / model_dump+重建
在典型数据规模下的峰值内存占用与耗时，为缓存实现选型提供数据依据。
"""

import json
import logging
import sys
import time
import tracemalloc
from copy import deepcopy
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas.response import ScenarioResponse  # noqa: E402

logger = logging.getLogger(__name__)


def _make_solver_result(route_count: int) -> dict:
    """构造近似真实求解结果的字典。"""
    routes = [
        {
            "vehicle_type": "4.2m" if i % 2 == 0 else "6.8m",
            "stops": [
                {"customer_id": j, "lat": 31.23 + j * 0.001, "lon": 121.47 + j * 0.001}
                for j in range(10)
            ],
            "distance_km": 50.0 + i,
            "drive_time_min": 60 + i,
        }
        for i in range(route_count)
    ]
    return {
        "solution": {
            "routes": routes,
            "total_distance": 100.0 * route_count,
            "total_drive_time": 120.0 * route_count,
        },
        "cost_result": {
            "total_cost": 1000.0 * route_count,
            "fuel_cost": 200.0 * route_count,
            "labor_cost": 300.0 * route_count,
            "fixed_cost": 400.0 * route_count,
            "carbon_emission_kg": 10.0 * route_count,
        },
        "solve_time_seconds": 1.5,
    }


def _make_scenario_responses(count: int) -> list[ScenarioResponse]:
    """构造近似真实场景列表响应。"""
    now = datetime(2026, 6, 30, 12, 0, 0)
    return [
        ScenarioResponse(
            id=i,
            name=f"场景_{i}",
            description="基准测试场景",
            customer_count=20 + i,
            solution_count=i % 3,
            created_at=now,
            updated_at=now,
        )
        for i in range(count)
    ]


def _measure(func, iterations: int = 100) -> dict:
    """测量函数多次执行的耗时与峰值内存。"""
    tracemalloc.start()
    start = time.perf_counter()
    for _ in range(iterations):
        _ = func()
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "iterations": iterations,
        "elapsed_ms": round(elapsed * 1000, 3),
        "peak_kb": round(peak / 1024, 2),
    }


def bench_solver_result_copy(sizes: list[int] | None = None, iterations: int = 100) -> dict:
    """对比求解结果缓存的 deepcopy 与 JSON 反序列化策略。"""
    sizes = sizes or [10, 100, 500]
    results = {}
    for size in sizes:
        result = _make_solver_result(size)
        serialized = json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        results[f"routes_{size}"] = {
            "size": size,
            "deepcopy": _measure(lambda r=result: deepcopy(r), iterations),
            "json_deserialize": _measure(lambda s=serialized: json.loads(s), iterations),
        }
    return results


def bench_scenario_response_copy(sizes: list[int] | None = None, iterations: int = 100) -> dict:
    """对比场景列表缓存的 model_copy(deep=True) 与 model_dump+重建策略。"""
    sizes = sizes or [10, 100, 500]
    results = {}
    for size in sizes:
        items = _make_scenario_responses(size)
        serialized = [item.model_dump() for item in items]

        results[f"items_{size}"] = {
            "size": size,
            "pydantic_deepcopy": _measure(
                lambda its=items: [item.model_copy(deep=True) for item in its], iterations
            ),
            "model_dump_rebuild": _measure(
                lambda srl=serialized: [ScenarioResponse(**d) for d in srl],
                iterations,
            ),
        }
    return results


def run(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or (Path(__file__).parent / "results")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "solver_result_cache": bench_solver_result_copy(),
        "scenario_response_cache": bench_scenario_response_copy(),
    }

    output_file = output_dir / "cache_memory_benchmark.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("缓存内存基准测试结果已保存: %s", output_file)
    return results


if __name__ == "__main__":
    run()
