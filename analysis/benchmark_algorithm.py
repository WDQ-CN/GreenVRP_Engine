"""可复现的 100 节点算法质量基准。

用法示例：
    python analysis/benchmark_algorithm.py --mode stage1 --stage1-time 30
    python analysis/benchmark_algorithm.py --mode alns --alns-time 60 --seeds 42,43,44
    python analysis/benchmark_algorithm.py --mode full --time-limit 60

stage1 解会缓存在 analysis/benchmark_artifacts/ 下，便于对 ALNS 改进做
同起点对比。所有成本均为 calculate_green_cost 的真实五维成本。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS, WORK_DAY_END_MIN, WORK_DAY_START_MIN
from config.vehicles import DEFAULT_VEHICLE_CONFIG
from core.cost import calculate_green_cost
from core.solver import GreenVRPSolver, solve_with_multiple_strategies_parallel
from optimization.alns import improve_solution_with_alns
from optimization.route_optimize import post_process_solution
from ortools.constraint_solver import routing_enums_pb2

ARTIFACT_DIR = Path(__file__).parent / "benchmark_artifacts"

# 与前端演示车队保持一致：5 辆 4.2m + 2 辆 7.6m
BENCHMARK_VEHICLE_CONFIG: Dict[str, Dict[str, Any]] = {
    "4.2m": {
        "capacity": 800,
        "fixed_cost": 200,
        "fuel_per_100km": 12,
        "speed_kmh": 40,
        "count": 5,
        "color": "#1f77b4",
    },
    "7.6m": {
        "capacity": 1500,
        "fixed_cost": 350,
        "fuel_per_100km": 18,
        "speed_kmh": 35,
        "count": 2,
        "color": "#2ca02c",
    },
}

STRATEGIES = {
    "gls": (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ),
    "tabu": (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
    ),
    "sa": (
        routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
        routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    ),
    "greedy": (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
    ),
    "pci": (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ),
}


def generate_customers(n_customers: int, seed: int) -> pd.DataFrame:
    """生成固定种子、可复现的北京城区配送实例（含仓库）。"""
    rng = np.random.default_rng(seed)
    depot_lat, depot_lon = 39.9042, 116.4074

    lats = depot_lat + rng.uniform(-0.12, 0.12, n_customers)
    lons = depot_lon + rng.uniform(-0.16, 0.16, n_customers)
    demands = rng.integers(20, 71, n_customers)
    service_times = rng.integers(10, 26, n_customers)
    tw_earliest = WORK_DAY_START_MIN + rng.integers(0, 241, n_customers)
    tw_latest = np.minimum(
        WORK_DAY_END_MIN,
        tw_earliest + rng.integers(120, 301, n_customers),
    )

    df = pd.DataFrame(
        {
            "id": range(n_customers + 1),
            "name": ["仓库"] + [f"客户{i}" for i in range(1, n_customers + 1)],
            "lat": [depot_lat, *lats],
            "lon": [depot_lon, *lons],
            "demand": [0, *demands.astype(int)],
            "service_time_min": [0, *service_times.astype(int)],
            "tw_earliest": [WORK_DAY_START_MIN, *tw_earliest.astype(int)],
            "tw_latest": [WORK_DAY_END_MIN, *tw_latest.astype(int)],
        }
    )
    return df


def _cost_params(late_penalty: float) -> Dict[str, Any]:
    params: Dict[str, Any] = {**DEFAULT_PARAMS}
    params["late_penalty_per_min"] = late_penalty
    return params


def _describe(solution: Dict[str, Any], config: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    cost = calculate_green_cost(solution, config, params)
    return {
        "cost": cost["total_cost"],
        "transport_cost": cost["transport_cost"],
        "labor_cost": cost["labor_cost"],
        "fixed_cost": cost["fixed_cost"],
        "penalty_cost": cost["penalty_cost"],
        "carbon_cost": cost["carbon_cost"],
        "carbon_kg": cost["carbon_emission_kg"],
        "distance_km": cost["total_distance_km"],
        "late_minutes": solution.get("total_late_minutes", 0),
        "vehicles": sum(solution.get("vehicles_used", {}).values()),
        "solve_time": solution.get("solve_time_seconds", 0),
    }


def _print_metrics(label: str, metrics: Dict[str, Any]) -> None:
    print(
        f"{label}: 总成本 {metrics['cost']:.2f} | "
        f"运输 {metrics['transport_cost']:.2f} | 人工 {metrics['labor_cost']:.2f} | "
        f"固定 {metrics['fixed_cost']:.2f} | 违约 {metrics['penalty_cost']:.2f} | "
        f"碳 {metrics['carbon_cost']:.2f} | 碳排 {metrics['carbon_kg']:.2f}kg | "
        f"迟到 {metrics['late_minutes']}min | {metrics['vehicles']}车 | "
        f"距离 {metrics['distance_km']:.1f}km | 耗时 {metrics['solve_time']}s"
    )


def _fleet_config(fleet: str) -> Dict[str, Dict[str, Any]]:
    if fleet in ("web", "web15"):
        config = {
            vehicle_type: dict(values)
            for vehicle_type, values in DEFAULT_VEHICLE_CONFIG.items()
        }
        if fleet == "web15":
            for values in config.values():
                values["count"] = 5
        else:
            config["4.2m"]["count"] = 5
            config["7.6m"]["count"] = 3
            config["9.6m"]["count"] = 2
        return config
    if fleet in ("prod", "five_a", "five_b", "five_c", "five_d", "prod_alt"):
        config = {
            vehicle_type: dict(values)
            for vehicle_type, values in DEFAULT_VEHICLE_CONFIG.items()
        }
        if fleet == "prod_alt":
            config["4.2m"]["count"] = 2
            config["7.6m"]["count"] = 2
            config["9.6m"]["count"] = 2
            return config
        if fleet == "five_a":
            config["4.2m"]["count"] = 3
            config["7.6m"]["count"] = 1
            config["9.6m"]["count"] = 1
        elif fleet == "five_b":
            config["4.2m"]["count"] = 3
            config["7.6m"]["count"] = 0
            config["9.6m"]["count"] = 2
        elif fleet == "five_c":
            config["4.2m"]["count"] = 2
            config["7.6m"]["count"] = 2
            config["9.6m"]["count"] = 1
        elif fleet == "five_d":
            config["4.2m"]["count"] = 1
            config["7.6m"]["count"] = 2
            config["9.6m"]["count"] = 2
        return config
    config = {
        vehicle_type: dict(values)
        for vehicle_type, values in BENCHMARK_VEHICLE_CONFIG.items()
    }
    if fleet == "five_e":
        config["4.2m"]["count"] = 4
        config["7.6m"]["count"] = 1
        return config
    if fleet == "fifteen":
        config["4.2m"]["count"] = 10
        config["7.6m"]["count"] = 5
        return config
    if fleet.startswith("small"):
        # 纯 4.2m 车队，数量由后缀决定，例如 small6 / small7 / small8。
        count = int(fleet[len("small"):])
        return {
            "4.2m": {
                **BENCHMARK_VEHICLE_CONFIG["4.2m"],
                "count": count,
            }
        }
    if fleet == "nine":
        config["4.2m"]["count"] = 7
        config["7.6m"]["count"] = 2
        return config
    if fleet == "six":
        config["7.6m"]["count"] = 1
    elif fleet == "six_alt":
        config["4.2m"]["count"] = 4
    elif fleet == "five":
        config["4.2m"]["count"] = 3
    return config


def _stage1_cache_path(
    n_customers: int,
    seed: int,
    stage1_time: int,
    fleet: str,
    strategy: str,
    depot_start: Optional[int] = None,
    speed_factor: Optional[float] = None,
    stage_late_penalty: float = 10.0,
    stage_fuel_price: float = 7.5,
    stage_carbon_price: float = 0.08,
    stage_hourly_wage: float = 0.0,
) -> Path:
    depot_suffix = f"_d{depot_start}" if depot_start is not None else ""
    speed_suffix = (
        f"_m{speed_factor:g}" if speed_factor is not None else ""
    )
    penalty_suffix = (
        f"_p{stage_late_penalty:g}"
        if stage_late_penalty != 10.0
        else ""
    )
    cost_suffix = ""
    if stage_fuel_price != 7.5 or stage_carbon_price != 0.08:
        cost_suffix = (
            f"_fp{stage_fuel_price:g}_cp{stage_carbon_price:g}"
        )
    wage_suffix = (
        f"_w{stage_hourly_wage:g}" if stage_hourly_wage != 0 else ""
    )
    return ARTIFACT_DIR / (
        f"stage1_n{n_customers}_seed{seed}_t{stage1_time}_{fleet}_"
        f"{strategy}{depot_suffix}{speed_suffix}{penalty_suffix}"
        f"{cost_suffix}{wage_suffix}.json"
    )


def build_stage1(
    customers_df: pd.DataFrame,
    config: Dict[str, Any],
    stage1_time: int,
    seed: int,
    force: bool,
    fleet: str,
    strategy: str,
    depot_start: Optional[int] = None,
    speed_factor: Optional[float] = None,
    stage_late_penalty: float = 10.0,
    stage_fuel_price: float = 7.5,
    stage_carbon_price: float = 0.08,
    stage_hourly_wage: float = 0.0,
) -> Dict[str, Any]:
    n_customers = len(customers_df) - 1
    cache_path = _stage1_cache_path(
        n_customers,
        seed,
        stage1_time,
        fleet,
        strategy,
        depot_start,
        speed_factor,
        stage_late_penalty,
        stage_fuel_price,
        stage_carbon_price,
        stage_hourly_wage,
    )
    if cache_path.exists() and not force:
        print(f"复用 stage1 解: {cache_path}")
        with cache_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    first_solution, metaheuristic = STRATEGIES[strategy]
    print(
        f"OR-Tools 首轮求解 ({stage1_time}s, {strategy})..."
    )
    solver = GreenVRPSolver(
        customers_df=customers_df,
        vehicle_config=config,
        time_penalty_per_min=stage_late_penalty,
        search_time_limit=stage1_time,
        depot_start_minute=depot_start,
        time_matrix_speed_factor=speed_factor,
        fuel_price=stage_fuel_price,
        carbon_price=stage_carbon_price,
        hourly_wage=stage_hourly_wage,
    )
    solution = solver.solve_with_params(
        first_solution_strategy=first_solution,
        metaheuristic=metaheuristic,
        time_limit=stage1_time,
    )
    if solution.get("solution_status") == "SUCCESS":
        solution = post_process_solution(solution, config)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as fh:
        json.dump(solution, fh, ensure_ascii=False, default=str)
    print(f"stage1 解已缓存: {cache_path}")
    return solution


def run_alns(
    stage1: Dict[str, Any],
    config: Dict[str, Any],
    alns_time: float,
    seeds: List[int],
    recombine: bool = False,
    recombine_time: float = 10.0,
    param_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    params = _cost_params(10.0)
    if param_overrides:
        params.update(param_overrides)
    before = _describe(stage1, config, params)
    _print_metrics("ALNS 起点", before)

    best_solution = stage1
    best_cost = before["cost"]
    rows: List[Dict[str, Any]] = []
    for seed in seeds:
        started = time.perf_counter()
        stats: Dict[str, Any] = {}
        candidate = improve_solution_with_alns(
            stage1,
            config,
            params,
            time_limit=alns_time,
            seed=seed,
            stats=stats,
            recombine=recombine,
            recombine_time=recombine_time,
        )
        elapsed = time.perf_counter() - started
        metrics = _describe(candidate, config, params)
        metrics["seed"] = seed
        metrics["wall_seconds"] = round(elapsed, 2)
        metrics["alns"] = stats
        rows.append(metrics)
        _print_metrics(f"seed={seed}", metrics)
        if stats:
            print(
                f"  ALNS 内部: {stats.get('iterations')} 次迭代 | "
                f"接受 {stats.get('accepted')} | 刷新最优 {stats.get('improvements')} | "
                f"最优迭代 {stats.get('best_iteration')} | "
                f"扰动 {stats.get('shakes', 0)} | "
                f"发车 {stats.get('start_times')} | "
                f"路线池 {stats.get('pool_size', 0)} | "
                f"重组 {'是' if stats.get('recombined') else '否'} | "
                f"内部成本 {stats.get('initial_cost', 0):.2f} -> "
                f"{stats.get('best_cost', 0):.2f}"
            )
            print(
                f"  破坏算子使用: {stats.get('destroy_totals')} | "
                f"修复算子使用: {stats.get('repair_totals')}"
            )
        if metrics["cost"] < best_cost - 1e-6:
            best_cost = metrics["cost"]
            best_solution = candidate

    improvement = before["cost"] - best_cost
    print(
        f"ALNS 最好结果: {best_cost:.2f} "
        f"(改进 {improvement:.2f}, {improvement / before['cost'] * 100:.2f}%)"
    )
    return best_solution, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="GreenVRP 算法质量基准")
    parser.add_argument("--mode", choices=["stage1", "alns", "full"], default="alns")
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage1-time", type=int, default=30)
    parser.add_argument("--alns-time", type=float, default=60.0)
    parser.add_argument("--time-limit", type=int, default=60)
    parser.add_argument("--seeds", type=str, default="42,43,44")
    parser.add_argument("--rebuild-stage1", action="store_true")
    parser.add_argument(
        "--fleet",
        type=str,
        default="default",
    )
    parser.add_argument(
        "--strategy", choices=list(STRATEGIES.keys()), default="gls"
    )
    parser.add_argument("--depot-start", type=int, default=None)
    parser.add_argument("--matrix-speed-factor", type=float, default=None)
    parser.add_argument("--stage-late-penalty", type=float, default=10.0)
    parser.add_argument("--stage-fuel-price", type=float, default=7.5)
    parser.add_argument("--stage-carbon-price", type=float, default=0.08)
    parser.add_argument("--stage-hourly-wage", type=float, default=0.0)
    parser.add_argument("--json-out", type=str, default="")
    parser.add_argument("--solution-out", type=str, default="")
    parser.add_argument("--recombine", action="store_true")
    parser.add_argument("--recombine-time", type=float, default=10.0)
    parser.add_argument("--temperature-ratio", type=float, default=None)
    parser.add_argument("--cooling-factor", type=float, default=None)
    parser.add_argument("--shake-fraction", type=float, default=None)
    parser.add_argument("--shake-stagnation-factor", type=float, default=None)
    parser.add_argument("--large-q-probability", type=float, default=None)
    parser.add_argument("--destroy-weights", type=str, default=None)
    parser.add_argument("--repair-weights", type=str, default=None)
    parser.add_argument("--q-low-divisor", type=int, default=None)
    parser.add_argument("--q-high-divisor", type=int, default=None)
    parser.add_argument("--large-q-low-divisor", type=int, default=None)
    parser.add_argument("--large-q-high-divisor", type=int, default=None)
    parser.add_argument("--shake-temperature-ratio", type=float, default=None)
    parser.add_argument("--weight-floor", type=float, default=None)
    parser.add_argument("--base-start-minute", type=int, default=None)
    parser.add_argument("--iteration-limit", type=int, default=None)
    parser.add_argument("--acceptance", choices=["sa", "lahc"], default=None)
    parser.add_argument("--lahc-length", type=int, default=None)
    args = parser.parse_args()

    customers_df = generate_customers(args.nodes, args.seed)
    config = _fleet_config(args.fleet)
    total_demand = int(customers_df["demand"].sum())
    total_capacity = sum(
        cfg["capacity"] * cfg["count"] for cfg in config.values()
    )
    print(
        f"实例: {args.nodes} 客户 | 总需求 {total_demand}kg | "
        f"车队总容量 {total_capacity}kg | 数据种子 {args.seed}"
    )
    assert total_demand <= total_capacity, "实例需求超过车队容量"

    if args.mode == "full":
        full_cost_params: Dict[str, Any] = dict(DEFAULT_PARAMS)
        if args.stage_fuel_price != 7.5:
            full_cost_params["stage_fuel_price"] = args.stage_fuel_price
        started = time.perf_counter()
        solution = solve_with_multiple_strategies_parallel(
            customers_df=customers_df,
            vehicle_config=config,
            time_penalty_per_min=10.0,
            time_limit=args.time_limit,
            cost_params=full_cost_params,
        )
        print(f"全流水线耗时 {time.perf_counter() - started:.1f}s")
        metrics = _describe(solution, config, _cost_params(10.0))
        _print_metrics("全流水线", metrics)
        if args.solution_out:
            Path(args.solution_out).write_text(
                json.dumps(solution, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return

    stage1 = build_stage1(
        customers_df,
        config,
        args.stage1_time,
        args.seed,
        args.rebuild_stage1,
        args.fleet,
        args.strategy,
        args.depot_start,
        args.matrix_speed_factor,
        args.stage_late_penalty,
        args.stage_fuel_price,
        args.stage_carbon_price,
        args.stage_hourly_wage,
    )
    params = _cost_params(10.0)
    if stage1.get("solution_status") != "SUCCESS" or not stage1.get("routes"):
        print(f"stage1 求解失败: {stage1.get('solution_status')}")
        return
    _print_metrics("stage1", _describe(stage1, config, params))

    if args.mode == "stage1":
        return

    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    overrides: Dict[str, Any] = {}
    if args.temperature_ratio is not None:
        overrides["alns_temperature_ratio"] = args.temperature_ratio
    if args.cooling_factor is not None:
        overrides["alns_cooling_factor"] = args.cooling_factor
    if args.shake_fraction is not None:
        overrides["alns_shake_fraction"] = args.shake_fraction
    if args.shake_stagnation_factor is not None:
        overrides["alns_shake_stagnation_factor"] = (
            args.shake_stagnation_factor
        )
    if args.large_q_probability is not None:
        overrides["alns_large_q_probability"] = args.large_q_probability
    if args.destroy_weights:
        overrides["alns_destroy_weights"] = [
            float(value)
            for value in args.destroy_weights.split(",")
            if value.strip()
        ]
    if args.repair_weights:
        overrides["alns_repair_weights"] = [
            float(value)
            for value in args.repair_weights.split(",")
            if value.strip()
        ]
    if args.q_low_divisor is not None:
        overrides["alns_q_low_divisor"] = args.q_low_divisor
    if args.q_high_divisor is not None:
        overrides["alns_q_high_divisor"] = args.q_high_divisor
    if args.large_q_low_divisor is not None:
        overrides["alns_large_q_low_divisor"] = args.large_q_low_divisor
    if args.large_q_high_divisor is not None:
        overrides["alns_large_q_high_divisor"] = args.large_q_high_divisor
    if args.shake_temperature_ratio is not None:
        overrides["alns_shake_temperature_ratio"] = (
            args.shake_temperature_ratio
        )
    if args.weight_floor is not None:
        overrides["alns_weight_floor"] = args.weight_floor
    if args.base_start_minute is not None:
        overrides["alns_base_start_minute"] = args.base_start_minute
    if args.iteration_limit is not None:
        overrides["alns_iteration_limit"] = args.iteration_limit
    if args.acceptance is not None:
        overrides["alns_acceptance"] = args.acceptance
    if args.lahc_length is not None:
        overrides["alns_lahc_length"] = args.lahc_length
    best, rows = run_alns(
        stage1,
        config,
        args.alns_time,
        seeds,
        recombine=args.recombine,
        recombine_time=args.recombine_time,
        param_overrides=overrides,
    )

    if args.solution_out:
        Path(args.solution_out).write_text(
            json.dumps(best, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
