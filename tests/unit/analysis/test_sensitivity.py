"""
单元测试：analysis/sensitivity.py — 敏感度分析
"""

import pandas as pd
import pytest

from analysis.sensitivity import SensitivityAnalyzer, SensitivityResult


class TestSensitivityResult:
    def test_to_dict(self):
        result = SensitivityResult(
            parameter_name="fuel_price",
            base_value=7.5,
            test_values=[6.0, 7.5, 9.0],
            results=[{"total_cost": 1000}, {"total_cost": 1200}, {"total_cost": 1400}],
            sensitivities={"total_cost": 0.85},
            impact_ranking=[("total_cost", 0.85)],
            summary=pd.DataFrame({
                "test_value": [6.0, 7.5, 9.0],
                "total_cost": [1000, 1200, 1400],
            }),
        )
        d = result.to_dict()
        assert d["parameter_name"] == "fuel_price"
        assert d["base_value"] == 7.5
        assert len(d["test_values"]) == 3
        assert d["sensitivities"]["total_cost"] == 0.85

    def test_sensitivity_result_attributes(self):
        result = SensitivityResult(
            parameter_name="carbon_price",
            base_value=0.08,
            test_values=[0.04, 0.08, 0.16],
            results=[{}, {}, {}],
            sensitivities={"carbon_cost": 0.92, "total_cost": 0.15},
            impact_ranking=[("carbon_cost", 0.92), ("total_cost", 0.15)],
            summary=pd.DataFrame(),
        )
        assert result.parameter_name == "carbon_price"
        assert len(result.sensitivities) == 2
        assert result.impact_ranking[0][0] == "carbon_cost"


class TestSensitivityAnalyzer:
    def test_init(self):
        def solver_fn(df, config, params):
            return {"total_distance": 100}
        analyzer = SensitivityAnalyzer(
            solver_func=solver_fn,
            base_params={"fuel_price": 7.5},
            base_vehicle_config={},
            base_customers=[],
        )
        assert analyzer.solver_func is solver_fn
        assert analyzer.base_params["fuel_price"] == 7.5
