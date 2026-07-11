"""
单元测试：data_types/solution.py — 求解结果数据类型
"""

from data_types.solution import Route, Solution, Stop


class TestStop:
    def test_create(self):
        s = Stop(node=1, lat=39.9, lon=116.4, arrival_time=500,
                  service_time=15, tw_earliest=480, tw_latest=600)
        assert s.node == 1
        assert s.arrival_time == 500

    def test_with_customer_info(self):
        s = Stop(node=1, customer_id=1, lat=39.9, lon=116.4,
                  demand=50, arrival_time=500, service_time=15)
        assert s.customer_id == 1
        assert s.demand == 50


class TestRoute:
    def test_create(self):
        r = Route(vehicle_id=0, vehicle_type="4.2m", distance_km=10.0)
        assert r.vehicle_id == 0
        assert r.distance_km == 10.0
        assert r.stops == []

    def test_with_stops(self):
        stop = Stop(node=1, lat=39.9, lon=116.4, arrival_time=500,
                     service_time=15, tw_earliest=480, tw_latest=600)
        r = Route(vehicle_id=0, vehicle_type="4.2m", stops=[stop],
                   distance_km=10.0, total_demand=50)
        assert len(r.stops) == 1
        assert r.total_demand == 50


class TestSolution:
    def test_defaults(self):
        s = Solution()
        assert s.solution_status == "UNKNOWN"
        assert s.routes == []
        assert s.total_distance == 0.0

    def test_with_routes(self):
        r = Route(vehicle_id=0, vehicle_type="4.2m", distance_km=10.0)
        s = Solution(routes=[r], total_distance=10.0,
                      vehicles_used={"4.2m": 1}, solution_status="SUCCESS")
        assert len(s.routes) == 1
        assert s.total_distance == 10.0
        assert s.solution_status == "SUCCESS"

    def test_to_dict(self):
        r = Route(vehicle_id=0, vehicle_type="4.2m", distance_km=10.0)
        s = Solution(routes=[r], total_distance=10.0,
                      vehicles_used={"4.2m": 1})
        d = s.to_dict()
        assert d["total_distance"] == 10.0
        assert len(d["routes"]) == 1
