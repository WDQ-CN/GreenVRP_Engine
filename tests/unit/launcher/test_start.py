"""
单元测试：启动器 (start.py, start_fast.py, start_optimized.py)
"""

import sys
import json
import os
import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# Fixtures: 预导入模块（处理模块级副作用）
# =============================================================================

def _import_launcher(module_name):
    """安全导入启动器模块（处理模块级 stdout/stderr 副作用）。"""
    import importlib
    # 模拟非 Windows 平台，避免模块级 stdout 包装（与 pytest 冲突）
    with patch.object(sys, "platform", "linux"), \
         patch("builtins.print"):  # 抑制启动时序日志
        mod = importlib.import_module(module_name)
    return mod


# =============================================================================
# 参数解析测试
# =============================================================================

class TestArgumentParsing:
    """命令行参数解析测试。"""

    def _test_main_with_args(self, module_name, argv, expected_func):
        mod = _import_launcher(module_name)
        with patch.object(sys, "argv", argv), \
             patch.object(mod, expected_func) as mock_func:
            try:
                mod.main()
            except SystemExit:
                pass
            mock_func.assert_called_once()
        return mock_func

    def test_start_web(self):
        """python start.py web。"""
        self._test_main_with_args("start", ["start.py", "web"], "start_web")

    def test_start_api(self):
        """python start.py api。"""
        self._test_main_with_args("start", ["start.py", "api"], "start_api")

    def test_start_api_with_port(self):
        """python start.py api --port 8001。"""
        mod = _import_launcher("start")
        with patch.object(sys, "argv", ["start.py", "api", "--port", "8001"]), \
             patch.object(mod, "start_api") as mock_api:
            try:
                mod.main()
            except SystemExit:
                pass
            mock_api.assert_called_once()
            args, kwargs = mock_api.call_args
            assert kwargs.get("port") == 8001

    def test_start_api_no_reload(self):
        """python start.py api --no-reload。"""
        mod = _import_launcher("start")
        with patch.object(sys, "argv", ["start.py", "api", "--no-reload"]), \
             patch.object(mod, "start_api") as mock_api:
            try:
                mod.main()
            except SystemExit:
                pass
            args, kwargs = mock_api.call_args
            assert kwargs.get("reload") is False

    def test_interactive_no_args(self):
        """python start.py → interactive_mode。"""
        self._test_main_with_args("start", ["start.py"], "interactive_mode")

    def test_start_fast_web(self):
        """start_fast.py web。"""
        self._test_main_with_args("start_fast", ["start_fast.py", "web"], "start_web")

    def test_start_fast_api(self):
        """start_fast.py api。"""
        self._test_main_with_args("start_fast", ["start_fast.py", "api"], "start_api")

    def test_start_optimized_web(self):
        """start_optimized.py web。"""
        self._test_main_with_args("start_optimized", ["start_optimized.py", "web"], "start_web")

    def test_start_optimized_api(self):
        """start_optimized.py api。"""
        self._test_main_with_args("start_optimized", ["start_optimized.py", "api"], "start_api")


# =============================================================================
# start_web 测试
# =============================================================================

class TestStartWeb:
    """start_web 使用 subprocess.run 启动 Streamlit。"""

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_streamlit_subprocess_call(self, module):
        mod = _import_launcher(module)
        with patch.object(mod, "subprocess") as mock_subproc:
            mock_subproc.run.return_value = MagicMock(returncode=0)
            mod.start_web()
            args = mock_subproc.run.call_args[0][0]
            assert "-m" in args
            assert "streamlit" in args
            assert "run" in args
            assert "web_app.py" in args

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_subprocess_failure(self, module):
        mod = _import_launcher(module)
        with patch.object(mod, "subprocess") as mock_subproc:
            mock_subproc.run.side_effect = FileNotFoundError
            with pytest.raises(FileNotFoundError):
                mod.start_web()


# =============================================================================
# start_api 测试
# =============================================================================

class TestStartApi:
    """start_api 测试。"""

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_default_port_with_reload(self, module):
        mod = _import_launcher(module)
        with patch.object(mod, "subprocess") as mock_subproc:
            mock_subproc.run.return_value = MagicMock(returncode=0)
            mod.start_api()
            args = mock_subproc.run.call_args[0][0]
            assert "uvicorn" in args
            assert "--reload" in args

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_custom_port_no_reload(self, module):
        mod = _import_launcher(module)
        with patch.object(mod, "subprocess") as mock_subproc:
            mock_subproc.run.return_value = MagicMock(returncode=0)
            mod.start_api(port=8001, reload=False)
            args = mock_subproc.run.call_args[0][0]
            assert "--port" in args
            port_idx = args.index("--port") + 1
            assert args[port_idx] == "8001"
            assert "--reload" not in args


# =============================================================================
# solve_cli 测试
# =============================================================================

class TestSolveCli:
    """solve_cli 命令行求解测试。"""

    @pytest.fixture
    def temp_csv(self, tmp_path):
        import pandas as pd
        csv_path = tmp_path / "test_data.csv"
        pd.DataFrame({
            "id": [0, 1], "name": ["仓库", "客户A"],
            "lat": [39.9, 40.0], "lon": [116.4, 116.5],
            "demand": [0, 50], "service_time_min": [0, 15],
            "tw_earliest": [480, 500], "tw_latest": [960, 600],
        }).to_csv(csv_path, index=False)
        return csv_path

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_solve_success(self, module, temp_csv):
        mod = _import_launcher(module)
        with patch("core.solver.solve_with_multiple_strategies") as mock_solve, \
             patch("core.cost.calculate_green_cost") as mock_cost, \
             patch("builtins.print"):
            mock_solve.return_value = {
                "solution_status": "SUCCESS", "total_distance": 100.0,
                "vehicles_used": {"4.2m": 2}, "total_late_minutes": 0,
            }
            mock_cost.return_value = {
                "total_cost": 1000, "transport_cost": 400, "labor_cost": 250,
                "fixed_cost": 200, "penalty_cost": 50, "carbon_emission_kg": 25,
            }
            mod.solve_cli(str(temp_csv))
            mock_solve.assert_called_once()
            mock_cost.assert_called_once()

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_file_not_found(self, module):
        mod = _import_launcher(module)
        with patch("builtins.print"):
            mod.solve_cli("nonexistent_file.csv")  # 不应抛异常

    @pytest.mark.parametrize("module", ["start", "start_fast"])
    def test_with_output_json(self, module, tmp_path):
        import pandas as pd
        mod = _import_launcher(module)
        csv_path = tmp_path / "in.csv"
        out_path = tmp_path / "out.json"
        pd.DataFrame({
            "id": [0, 1], "name": ["仓库", "客户A"],
            "lat": [39.9, 40.0], "lon": [116.4, 116.5],
            "demand": [0, 50], "service_time_min": [0, 15],
            "tw_earliest": [480, 500], "tw_latest": [960, 600],
        }).to_csv(csv_path, index=False)

        with patch("core.solver.solve_with_multiple_strategies") as mock_solve, \
             patch("core.cost.calculate_green_cost") as mock_cost, \
             patch("builtins.print"):
            mock_solve.return_value = {
                "solution_status": "SUCCESS", "total_distance": 100.0,
                "vehicles_used": {"4.2m": 2}, "total_late_minutes": 0,
            }
            mock_cost.return_value = {
                "total_cost": 1000, "transport_cost": 400, "labor_cost": 250,
                "fixed_cost": 200, "penalty_cost": 50, "carbon_emission_kg": 25,
            }
            mod.solve_cli(str(csv_path), output_file=str(out_path))
            assert out_path.exists()
            with open(out_path) as f:
                data = json.load(f)
                assert "solution" in data
                assert "cost_result" in data


# =============================================================================
# interactive_mode 测试
# =============================================================================

class TestInteractiveMode:
    """interactive_mode 交互式菜单测试。"""

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_choice_web(self, module):
        mod = _import_launcher(module)
        with patch("builtins.input", return_value="1"), \
             patch.object(mod, "start_web") as mock_web, \
             patch("builtins.print"):
            mod.interactive_mode()
            mock_web.assert_called_once()

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_choice_api_default(self, module):
        mod = _import_launcher(module)
        inputs = iter(["2", ""])
        with patch("builtins.input", lambda *a: next(inputs)), \
             patch.object(mod, "start_api") as mock_api, \
             patch("builtins.print"):
            mod.interactive_mode()
            mock_api.assert_called_once()

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_choice_api_custom_port(self, module):
        mod = _import_launcher(module)
        inputs = iter(["2", "8001"])
        with patch("builtins.input", lambda *a: next(inputs)), \
             patch.object(mod, "start_api") as mock_api, \
             patch("builtins.print"):
            mod.interactive_mode()
            args, kwargs = mock_api.call_args
            assert kwargs.get("port") == 8001

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_choice_exit(self, module):
        mod = _import_launcher(module)
        with patch("builtins.input", return_value="3"), \
             patch.object(mod, "start_web") as mock_web, \
             patch.object(mod, "start_api") as mock_api, \
             patch("builtins.print"):
            mod.interactive_mode()
            mock_web.assert_not_called()
            mock_api.assert_not_called()

    @pytest.mark.parametrize("module", ["start", "start_fast", "start_optimized"])
    def test_invalid_choice(self, module):
        mod = _import_launcher(module)
        with patch("builtins.input", return_value="x"), \
             patch("builtins.print") as mock_print:
            mod.interactive_mode()
            assert any("无效" in str(c) for c in mock_print.call_args_list)


# =============================================================================
# start_optimized.py 特有测试
# =============================================================================

class TestOptimizedImports:
    """start_optimized.py 优化导入机制测试。"""

    def test_lazy_import_caching(self):
        mod = _import_launcher("start_optimized")
        result1 = mod._lazy_import("json")
        result2 = mod._lazy_import("json")
        assert result1 is result2  # 缓存命中

    def test_lazy_import_alias(self):
        mod = _import_launcher("start_optimized")
        import json as real_json
        result = mod._lazy_import("json", alias="my_json")
        assert result is real_json
        assert mod._import_cache.get("my_json") is real_json

    def test_timing_disabled_by_default(self):
        """不设置 GREENVRP_PROFILE_STARTUP 时 _log_timing 不打印。"""
        mod = _import_launcher("start_optimized")
        with patch("builtins.print") as mock_print:
            mod._log_timing("test_point")
            mock_print.assert_not_called()
