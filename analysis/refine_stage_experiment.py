"""Experiment: run the full refinement pipeline on a cached stage solution."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from core.solver import refine_solution_with_load_ratios

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "benchmark_algorithm", Path(__file__).parent / "benchmark_algorithm.py"
)
_benchmark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_benchmark)

ARTIFACTS = Path(__file__).parent / "benchmark_artifacts"
CONFIG: Dict[str, Dict[str, Any]] = {
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
        "count": 1,
        "color": "#2ca02c",
    },
}


def main() -> None:
    stage_name = sys.argv[1]
    stage_fuel_price = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    with (ARTIFACTS / stage_name).open("r", encoding="utf-8") as handle:
        stage = json.load(handle)
    customers = _benchmark.generate_customers(100, 42)
    params = {**DEFAULT_PARAMS, "late_penalty_per_min": 10.0}
    before = calculate_green_cost(stage, CONFIG, params)["total_cost"]
    refined = refine_solution_with_load_ratios(
        stage,
        customers,
        CONFIG,
        time_penalty_per_min=10.0,
        time_limit=30,
        cost_params=params,
        stage_fuel_price=stage_fuel_price,
    )
    after = calculate_green_cost(refined, CONFIG, params)["total_cost"]
    print(
        f"{stage_name}: actual {before:.2f} -> {after:.2f}, "
        f"vehicles {sum(refined.get('vehicles_used', {}).values())}, "
        f"distance {refined.get('total_distance')}"
    )


if __name__ == "__main__":
    main()
