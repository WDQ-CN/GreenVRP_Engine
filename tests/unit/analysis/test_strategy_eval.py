"""
单元测试：analysis/strategy_eval.py — 策略效果评估
"""

import pandas as pd
import pytest

from analysis.strategy_eval import EvaluationResult, StrategyEvaluator


class TestEvaluationResult:
    def test_to_dict(self):
        result = EvaluationResult(
            strategies=["fast", "balanced", "thorough"],
            time_limits=[30, 60],
            results_matrix={
                "fast": [{"total_cost": 1000}, {"total_cost": 950}],
                "balanced": [{"total_cost": 900}, {"total_cost": 880}],
            },
            performance_metrics={
                "fast": {"avg_cost": 975, "stability": 0.8},
                "balanced": {"avg_cost": 890, "stability": 0.9},
            },
            best_strategy="balanced",
            stability_scores={"fast": 0.8, "balanced": 0.9},
            summary=pd.DataFrame(),
            recommendations=["推荐 balanced 策略"],
        )
        d = result.to_dict()
        assert d["best_strategy"] == "balanced"
        assert len(d["strategies"]) == 3
        assert d["stability_scores"]["balanced"] == 0.9

    def test_evaluation_result_empty(self):
        result = EvaluationResult(
            strategies=[],
            time_limits=[],
            results_matrix={},
            performance_metrics={},
            best_strategy="",
            stability_scores={},
            summary=pd.DataFrame(),
            recommendations=[],
        )
        assert result.best_strategy == ""
        assert len(result.recommendations) == 0


class TestStrategyEvaluator:
    def test_init(self):
        def solver_fn(df, config, params):
            return {"total_distance": 100}

        evaluator = StrategyEvaluator(
            solver_func=solver_fn,
            customers=[],
            vehicle_config={},
            params={"fuel_price": 7.5},
        )
        assert evaluator.solver_func is solver_fn
        assert evaluator.params["fuel_price"] == 7.5
