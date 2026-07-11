"""
单元测试：data_types/cost.py — 成本数据类型
"""

from data_types.cost import CarbonEfficiency, CostBreakdown, CostResult


class TestCostBreakdown:
    def test_defaults(self):
        cb = CostBreakdown()
        assert cb.transport_cost == 0.0
        assert cb.fixed_cost == 0.0
        assert cb.labor_cost == 0.0
        assert cb.carbon_cost == 0.0
        assert cb.penalty_cost == 0.0
        assert cb.total_cost == 0.0

    def test_with_values(self):
        cb = CostBreakdown(transport_cost=100, fixed_cost=50,
                            labor_cost=75, carbon_cost=20, penalty_cost=5)
        assert cb.transport_cost == 100
        assert cb.total_cost == 250

    def test_total_cost_property(self):
        cb = CostBreakdown(1, 2, 3, 4, 5)
        assert cb.total_cost == 15


class TestCostResult:
    def test_defaults(self):
        cr = CostResult()
        assert cr.carbon_emission_kg == 0.0
        assert cr.total_distance_km == 0.0
        assert cr.total_time_min == 0.0
        assert cr.vehicle_count == 0
        assert cr.total_cost == 0.0

    def test_with_values(self):
        cb = CostBreakdown(100, 50, 75, 20, 5)
        cr = CostResult(breakdown=cb, carbon_emission_kg=25.0,
                         total_distance_km=100.0, total_time_min=120.0,
                         vehicle_count=2)
        assert cr.total_cost == 250
        assert cr.carbon_emission_kg == 25.0
        assert cr.total_distance_km == 100.0
        assert cr.vehicle_count == 2


class TestCarbonEfficiency:
    def test_defaults(self):
        ce = CarbonEfficiency()
        assert ce.carbon_per_km == 0.0
        assert ce.carbon_per_customer == 0.0
        assert ce.total_carbon_kg == 0.0

    def test_with_values(self):
        ce = CarbonEfficiency(total_carbon_kg=25.0, carbon_per_km=0.3,
                               carbon_per_customer=5.0, carbon_per_kg_demand=0.1)
        assert ce.carbon_per_km == 0.3
        assert ce.total_carbon_kg == 25.0
        assert ce.carbon_per_kg_demand == 0.1
