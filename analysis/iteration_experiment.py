"""固定 stage1 解与随机种子，比较 ALNS 迭代预算对结果质量的影响。

用法：
    python analysis/iteration_experiment.py --iterations 2000,4000,6000 \
        --seeds 42,47,49,60,62,70,71,91 --workers 8
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from optimization.alns import improve_solution_with_alns

from benchmark_algorithm import BENCHMARK_VEHICLE_CONFIG

ARTIFACTS = Path(__file__).parent / "benchmark_artifacts"


def _fifteen_config():
    config = {
        vehicle_type: dict(values)
        for vehicle_type, values in BENCHMARK_VEHICLE_CONFIG.items()
    }
    config["4.2m"]["count"] = 10
    config["7.6m"]["count"] = 5
    return config


def _run_task(
    payload: Tuple[str, int, int, float]
) -> Dict[str, Any]:
    stage1_path, seed, iterations, time_limit = payload
    with open(stage1_path, "r", encoding="utf-8") as fh:
        stage1 = json.load(fh)
    config = _fifteen_config()
    params = {
        **DEFAULT_PARAMS,
        "late_penalty_per_min": 10.0,
        "alns_iteration_limit": iterations,
    }
    solution = improve_solution_with_alns(
        stage1,
        config,
        params,
        time_limit=time_limit,
        seed=seed,
    )
    cost = calculate_green_cost(solution, config, params)
    return {
        "iterations": iterations,
        "seed": seed,
        "cost": cost["total_cost"],
        "transport": cost["transport_cost"],
        "labor": cost["labor_cost"],
        "fixed": cost["fixed_cost"],
        "penalty": cost["penalty_cost"],
        "carbon": cost["carbon_cost"],
        "distance_km": cost["total_distance_km"],
        "vehicles": sum(solution.get("vehicles_used", {}).values()),
        "late_minutes": solution.get("total_late_minutes", 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=str, default="2000,4000,6000")
    parser.add_argument(
        "--seeds", type=str, default="42,47,49,60,62,70,71,91"
    )
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--stage1",
        type=str,
        default=str(
            ARTIFACTS / "stage1_n100_seed42_t30_fifteen_gls.json"
        ),
    )
    parser.add_argument("--json-out", type=str, default="")
    args = parser.parse_args()

    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    iteration_limits = [
        int(item) for item in args.iterations.split(",") if item.strip()
    ]
    with open(args.stage1, "r", encoding="utf-8") as fh:
        stage1 = json.load(fh)
    print(
        f"stage1: {len(stage1.get('routes', []))} 条路线 | "
        f"距离 {stage1.get('total_distance', 0):.1f}km | "
        f"迟到 {stage1.get('total_late_minutes', 0)}min"
    )

    tasks = [
        (args.stage1, seed, iterations, args.time_limit)
        for iterations in iteration_limits
        for seed in seeds
    ]
    rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_run_task, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                row = future.result()
            except Exception as exc:  # pragma: no cover - diagnostics
                print(f"iterations={task[2]} seed={task[1]} 失败: {exc}")
                continue
            rows.append(row)
            print(
                f"iterations={row['iterations']} seed={row['seed']}: "
                f"总成本 {row['cost']:.2f} | {row['vehicles']}车 | "
                f"距离 {row['distance_km']:.1f}km"
            )

    print("\n汇总：")
    for iterations in iteration_limits:
        costs = [
            row["cost"] for row in rows if row["iterations"] == iterations
        ]
        if not costs:
            continue
        print(
            f"iterations={iterations}: 均值 {statistics.mean(costs):.2f} | "
            f"最小 {min(costs):.2f} | 最大 {max(costs):.2f} | "
            f"样本 {len(costs)}"
        )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()