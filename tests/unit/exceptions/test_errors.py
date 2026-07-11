"""
单元测试：exceptions/errors.py — 异常层次结构
"""

from exceptions.errors import (
    ConfigurationError,
    CostCalculationError,
    DistanceCalculationError,
    GreenVRPError,
    JobNotFoundError,
    JobTimeoutError,
    SolverError,
    TrackingError,
    ValidationError,
)


class TestGreenVRPError:
    def test_base_exception(self):
        e = GreenVRPError("测试错误")
        assert str(e) == "测试错误"
        assert e.error_code == "GREENVRP_ERROR"
        assert e.details == {}

    def test_with_details(self):
        e = GreenVRPError("错误", error_code="CUSTOM", details={"key": "val"})
        assert e.error_code == "CUSTOM"
        assert e.details["key"] == "val"

    def test_to_dict(self):
        e = GreenVRPError("错误信息", error_code="ERR_001", details={"field": "x"})
        d = e.to_dict()
        assert d["error"] == "ERR_001"
        assert d["message"] == "错误信息"
        assert d["details"]["field"] == "x"


class TestSolverError:
    def test_default_code(self):
        e = SolverError("求解失败")
        assert e.error_code == "SOLVER_ERROR"

    def test_custom_code(self):
        e = SolverError("超时", error_code="TIMEOUT")
        assert e.error_code == "TIMEOUT"


class TestValidationError:
    def test_with_field(self):
        e = ValidationError("无效数据", field="lat", value=95.0)
        assert e.error_code == "VALIDATION_ERROR"
        assert e.details["field"] == "lat"
        assert e.details["value"] == "95.0"

    def test_without_field(self):
        e = ValidationError("未知错误")
        assert "field" not in e.details


class TestConfigurationError:
    def test_with_key(self):
        e = ConfigurationError("配置缺失", config_key="DB_URL")
        assert e.details["config_key"] == "DB_URL"


class TestDistanceCalculationError:
    def test_with_coords(self):
        e = DistanceCalculationError("计算失败", lat1=39.9, lon1=116.4)
        assert e.details["lat1"] == 39.9
        assert e.details["lon1"] == 116.4


class TestCostCalculationError:
    def test_with_type(self):
        e = CostCalculationError("计算异常", cost_type="transport")
        assert e.details["cost_type"] == "transport"


class TestTrackingError:
    def test_with_vehicle(self):
        e = TrackingError("追踪失败", vehicle_id=5)
        assert e.details["vehicle_id"] == 5


class TestJobNotFoundError:
    def test_format(self):
        e = JobNotFoundError("job-001")
        assert "job-001" in e.message
        assert e.details["job_id"] == "job-001"


class TestJobTimeoutError:
    def test_format(self):
        e = JobTimeoutError("job-001", timeout_seconds=600)
        assert "job-001" in e.message
        assert "600" in e.message
        assert e.details["timeout_seconds"] == 600
