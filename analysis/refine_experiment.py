"""Experiment: re-intensify a saved solution with a fresh ALNS run."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.constants import DEFAULT_PARAMS
from core.cost import calculate_green_cost
from core.solver import _two_opt_star_polish
from optimization.alns import improve_solution_with_alns
from utils.time_profile import peak_avoidance_start_minute

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
    solution_name = sys.argv[1] if len(sys.argv) > 1 else "full_t30_v32_sol.json"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    with (ARTIFACTS / solution_name).open("r", encoding="utf-8") as handle:
        base = json.load(handle)

    params = {**DEFAULT_PARAMS, "late_penalty_per_min": 10.0}
    before = calculate_green_cost(base, CONFIG, params)["total_cost"]
    improved = improve_solution_with_alns(
        base,
        CONFIG,
        {
            **params,
            "alns_base_start_minute": peak_avoidance_start_minute(),
            "alns_iteration_limit": 2000,
        },
        time_limit=60.0,
        seed=seed,
    )
    refined = _two_opt_star_polish(
        improved,
        CONFIG,
        params,
        20.0,
        include_segment=True,
        include_pairwise=True,
    )
    candidate = refined if refined is not None else improved
    after = calculate_green_cost(candidate, CONFIG, params)["total_cost"]
    print(
        f"{solution_name} seed={seed}: actual {before:.2f} -> {after:.2f}, "
        f"distance {candidate['total_distance']:.1f}km, "
        f"late {candidate['total_late_minutes']}"
    )
    print(f"improved: {after < before - 1e-6}")


if __name__ == "__main__":
    main()
