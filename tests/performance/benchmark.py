"""
GreenVRP 性能基准测试套件

用于对比优化前后的性能表现，包括：
- 距离矩阵构建速度
- 求解器收敛时间
- 内存占用
- 多目标优化Pareto前沿计算效率
"""

import statistics

# 设置项目路径
import sys
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.distance import (
    build_distance_matrix,
)
from core.solver import GreenVRPSolver


@dataclass
class BenchmarkResult:
    """基准测试结果。"""

    name: str
    execution_time_ms: float
    memory_peak_mb: float
    iterations: int
    std_dev_ms: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "memory_peak_mb": round(self.memory_peak_mb, 2),
            "iterations": self.iterations,
            "std_dev_ms": round(self.std_dev_ms, 2),
            "metadata": self.metadata,
        }


@contextmanager
def measure_performance(name: str):
    """性能测量上下文管理器。"""
    tracemalloc.start()
    time.perf_counter()
    yield
    time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()


def generate_random_customers(n: int, seed: int = 42) -> pd.DataFrame:
    """生成随机客户数据。"""
    rng = np.random.default_rng(seed)

    # 生成中国某城市周边的坐标
    base_lat, base_lon = 31.2304, 121.4737  # 上海

    data = {
        "id": range(n),
        "name": [f"客户_{i}" for i in range(n)],
        "lat": base_lat + rng.uniform(-0.5, 0.5, n),
        "lon": base_lon + rng.uniform(-0.5, 0.5, n),
        "demand": rng.integers(1, 100, n),
        "service_time_min": rng.integers(5, 30, n),
        "tw_earliest": rng.integers(0, 480, n),
        "tw_latest": rng.integers(540, 1080, n),
    }

    df = pd.DataFrame(data)
    # 确保时间窗有效
    df["tw_latest"] = np.maximum(df["tw_latest"], df["tw_earliest"] + 60)
    return df


def benchmark_distance_matrix(
    sizes: list[int] = None,
    iterations: int = 5,
) -> list[BenchmarkResult]:
    """基准测试距离矩阵构建。"""
    if sizes is None:
        sizes = [50, 100, 200, 500, 1000]
    results = []

    for size in sizes:
        # 生成测试数据
        customers = generate_random_customers(size)
        locations = list(zip(customers["lat"], customers["lon"], strict=False))

        # 测量密集矩阵性能
        times_dense = []
        for _ in range(iterations):
            time.perf_counter()
            tracemalloc.start()

            start = time.perf_counter()
            build_distance_matrix(locations, use_sparse=False)
            end = time.perf_counter()

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            times_dense.append((end - start) * 1000)

        # 测量稀疏矩阵性能（大规模）
        if size >= 500:
            times_sparse = []
            for _ in range(iterations):
                start = time.perf_counter()
                build_distance_matrix(locations, use_sparse=True)
                end = time.perf_counter()
                times_sparse.append((end - start) * 1000)

            sparse_result = BenchmarkResult(
                name=f"sparse_matrix_{size}",
                execution_time_ms=statistics.mean(times_sparse),
                memory_peak_mb=0,  # 需要单独测量
                iterations=iterations,
                std_dev_ms=statistics.stdev(times_sparse) if len(times_sparse) > 1 else 0,
                metadata={"size": size, "type": "sparse"},
            )
            results.append(sparse_result)

        result = BenchmarkResult(
            name=f"dense_matrix_{size}",
            execution_time_ms=statistics.mean(times_dense),
            memory_peak_mb=peak / 1024 / 1024,
            iterations=iterations,
            std_dev_ms=statistics.stdev(times_dense) if len(times_dense) > 1 else 0,
            metadata={"size": size, "type": "dense"},
        )
        results.append(result)

    return results


def benchmark_solver(
    sizes: list[int] = None,
    iterations: int = 3,
) -> list[BenchmarkResult]:
    """基准测试求解器性能。"""
    if sizes is None:
        sizes = [20, 50, 100]
    results = []

    for size in sizes:
        customers = generate_random_customers(size)

        # 标准车型配置
        vehicle_config = {
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

        times = []
        for _ in range(iterations):
            try:
                start = time.perf_counter()

                solver = GreenVRPSolver(
                    customers_df=customers,
                    vehicle_config=vehicle_config,
                    search_time_limit=30,
                )
                solution = solver.solve()

                end = time.perf_counter()
                times.append((end - start) * 1000)

            except Exception:
                break

        if times:
            result = BenchmarkResult(
                name=f"solver_{size}",
                execution_time_ms=statistics.mean(times),
                memory_peak_mb=0,
                iterations=len(times),
                std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
                metadata={
                    "size": size,
                    "solution_status": solution.get("solution_status", "UNKNOWN"),
                },
            )
            results.append(result)
        else:
            pass

    return results


def run_all_benchmarks() -> dict[str, list[BenchmarkResult]]:
    """运行所有基准测试。"""

    results = {
        "distance_matrix": benchmark_distance_matrix(
            sizes=[50, 100, 200, 500],
            iterations=5,
        ),
        "solver": benchmark_solver(
            sizes=[20, 50, 100],
            iterations=3,
        ),
    }

    # 汇总报告

    for _category, benchmarks in results.items():
        for _b in benchmarks:
            pass

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()
