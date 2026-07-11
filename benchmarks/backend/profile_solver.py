"""
后端求解器与距离矩阵性能分析脚本

使用 cProfile 采集求解器、距离矩阵构建、时间矩阵构建的热点函数，
输出排序后的累计耗时与调用次数，便于识别优化点。
"""

import cProfile
import json
import logging
import pstats
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.distance import DistanceMatrixCache, build_distance_matrix  # noqa: E402
from core.solver import GreenVRPSolver  # noqa: E402


def _generate_customers(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base_lat, base_lon = 31.2304, 121.4737
    df = pd.DataFrame(
        {
            "id": range(n),
            "name": [f"客户_{i}" for i in range(n)],
            "lat": base_lat + rng.uniform(-0.5, 0.5, n),
            "lon": base_lon + rng.uniform(-0.5, 0.5, n),
            "demand": rng.integers(1, 100, n),
            "service_time_min": rng.integers(5, 30, n),
            "tw_earliest": rng.integers(0, 480, n),
            "tw_latest": rng.integers(540, 1080, n),
        }
    )
    df["tw_latest"] = np.maximum(df["tw_latest"], df["tw_earliest"] + 60)
    return df


def _vehicle_config() -> dict:
    return {
        "small": {
            "capacity": 200,
            "count": 10,
            "speed_kmh": 40,
            "fixed_cost": 100,
            "fuel_per_100km": 10,
            "color": "#3498db",
        },
        "large": {
            "capacity": 500,
            "count": 5,
            "speed_kmh": 35,
            "fixed_cost": 200,
            "fuel_per_100km": 18,
            "color": "#e74c3c",
        },
    }


def profile_distance_matrix(sizes: list[int] | None = None) -> dict:
    sizes = sizes or [100, 500, 1000]
    results = {}
    for size in sizes:
        customers = _generate_customers(size)
        locations = list(zip(customers["lat"], customers["lon"], strict=False))

        profiler = cProfile.Profile()
        profiler.enable()
        start = time.perf_counter()
        build_distance_matrix(locations)
        elapsed = time.perf_counter() - start
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)

        # 累计耗时 Top 10（排除 cProfile 自身）
        top = [
            {"func": func, "ncalls": cc, "tottime": tt, "cumtime": ct}
            for func, (cc, nc, tt, ct, _callers) in stats.stats.items()
        ]
        top.sort(key=lambda x: x["cumtime"], reverse=True)
        top = top[:10]

        results[f"distance_matrix_{size}"] = {
            "size": size,
            "elapsed_ms": round(elapsed * 1000, 2),
            "top_hotspots": top,
        }
    return results


def profile_solver(sizes: list[int] | None = None, time_limit: int = 10) -> dict:
    sizes = sizes or [20, 50]
    results = {}
    vehicle_config = _vehicle_config()

    # 清空距离矩阵缓存，确保每次测量完整路径
    cache = DistanceMatrixCache()
    cache.clear()

    for size in sizes:
        customers = _generate_customers(size)

        profiler = cProfile.Profile()
        profiler.enable()
        start = time.perf_counter()
        solver = GreenVRPSolver(
            customers_df=customers,
            vehicle_config=vehicle_config,
            search_time_limit=time_limit,
            use_cache=False,
        )
        solution = solver.solve()
        elapsed = time.perf_counter() - start
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        top = [
            {"func": f"{func[0]}:{func[1]}({func[2]})", "ncalls": cc, "tottime": tt, "cumtime": ct}
            for func, (cc, nc, tt, ct, _callers) in stats.stats.items()
        ]
        top.sort(key=lambda x: x["cumtime"], reverse=True)
        top = top[:10]

        results[f"solver_{size}"] = {
            "size": size,
            "time_limit": time_limit,
            "solve_status": solution.get("solution_status"),
            "solve_time_reported_s": solution.get("solve_time_seconds"),
            "elapsed_ms": round(elapsed * 1000, 2),
            "top_hotspots": top,
        }
    return results


def run(output_dir: Path | None = None) -> dict:
    output_dir = output_dir or (Path(__file__).parent / "results")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "distance_matrix": profile_distance_matrix(),
        "solver": profile_solver(),
    }

    output_file = output_dir / "backend_profile.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("后端分析结果已保存: %s", output_file)
    return results


if __name__ == "__main__":
    run()
