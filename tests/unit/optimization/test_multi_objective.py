"""
单元测试：optimization/multi_objective.py — 多目标优化（纯函数部分）
"""

import numpy as np
import pandas as pd
import pytest
from pytest import approx

from pytest import approx

from optimization.multi_objective import (
    MultiObjectiveOptimizer,
    ObjectiveWeights,
    ParetoFrontResult,
)


class TestObjectiveWeights:
    def test_defaults(self):
        w = ObjectiveWeights()
        assert w.cost == 0.4
        assert w.carbon == 0.3
        assert w.time == 0.2
        assert w.service_level == 0.1

    def test_normalize(self):
        w = ObjectiveWeights(cost=2.0, carbon=2.0, time=1.0, service_level=1.0)
        normalized = w.normalize()
        assert normalized.cost == approx(2.0 / 6.0)

    def test_to_list(self):
        w = ObjectiveWeights(cost=0.5, carbon=0.3, time=0.1, service_level=0.1)
        lst = w.to_list()
        assert len(lst) == 4
        assert lst[0] == 0.5

    def test_from_dict(self):
        d = {"cost": 0.4, "carbon": 0.3, "time": 0.2}
        w = ObjectiveWeights.from_dict(d)
        # 默认 service_level 可能为 0.1 而非 0.0
        assert w.cost == pytest.approx(0.4, abs=1e-6)
        assert w.carbon == pytest.approx(0.3, abs=1e-6)


class TestDomination:
    @pytest.fixture
    def opt(self):
        return MultiObjectiveOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})

    def test_dominates(self, opt):
        assert opt._dominates(
            {"total_cost": 400, "carbon_emission_kg": 20},
            {"total_cost": 500, "carbon_emission_kg": 25},
        ) is True

    def test_not_dominated(self, opt):
        assert opt._dominates(
            {"total_cost": 400, "carbon_emission_kg": 30},
            {"total_cost": 500, "carbon_emission_kg": 25},
        ) is False

    def test_equal(self, opt):
        assert opt._dominates(
            {"total_cost": 500, "carbon_emission_kg": 25},
            {"total_cost": 500, "carbon_emission_kg": 25},
        ) is False


class TestFilterParetoFront:
    @pytest.fixture
    def opt(self):
        return MultiObjectiveOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})

    def test_basic(self, opt):
        values = [
            {"total_cost": 500, "carbon_emission_kg": 25},
            {"total_cost": 600, "carbon_emission_kg": 30},
            {"total_cost": 400, "carbon_emission_kg": 35},
        ]
        front = opt._filter_pareto_front(values)
        assert len(front) >= 2

    def test_single(self, opt):
        front = opt._filter_pareto_front([{"cost": 500, "carbon": 25}])
        assert len(front) == 1


class TestGenerateWeightGrid:
    @pytest.fixture
    def opt(self):
        return MultiObjectiveOptimizer(lambda *a: {}, [], {}, {"fuel_price": 7.5})

    def test_generates(self, opt):
        weights = opt._generate_weight_grid(num_points=5)
        assert len(weights) == 5
        for w in weights:
            assert isinstance(w, ObjectiveWeights)
